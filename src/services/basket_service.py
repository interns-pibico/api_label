"""Business logic for the Cesta de la Compra (Shopping Basket) feature."""

import asyncio
import logging
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.db.repositories.basket_repository import BasketRepository
from src.db.repositories.product_repository import ProductRepository
from src.models.baskets import Basket, BasketItem
from src.schemas.basket import (
    BasketCreate,
    BasketDetailResponse,
    BasketItemCreate,
    BasketItemResponse,
    BasketRename,
    BasketSearchResult,
    BasketSummary,
    OfertaInfo,
)
from src.services.basket_pdf import generate_basket_pdf
from src.services.integrations.openfoodfacts import lookup_barcode as off_lookup_barcode

logger = logging.getLogger(__name__)
settings = get_settings()

MAX_BASKETS = 3
MAX_ITEMS_PER_BASKET = 10


class BasketService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = BasketRepository(db)
        self.db = db

    # ── List / Create / Rename / Delete baskets ────────────────────────────────

    async def list_baskets(self, user_id: UUID) -> list[BasketSummary]:
        rows = await self.repo.get_by_user(user_id)
        return [
            BasketSummary(
                id=basket.id,
                name=basket.name,
                item_count=count,
                created_at=basket.created_at,
                updated_at=basket.updated_at,
            )
            for basket, count in rows
        ]

    async def create_basket(self, user_id: UUID, data: BasketCreate) -> BasketSummary:
        count = await self.repo.count_by_user(user_id)
        if count >= MAX_BASKETS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Límite de {MAX_BASKETS} cestas alcanzado",
            )
        basket = Basket(user_id=user_id, name=data.name)
        self.db.add(basket)
        await self.db.commit()
        await self.db.refresh(basket)
        return BasketSummary(
            id=basket.id,
            name=basket.name,
            item_count=0,
            created_at=basket.created_at,
            updated_at=basket.updated_at,
        )

    async def get_basket_detail(
        self, basket_id: UUID, user_id: UUID
    ) -> BasketDetailResponse:
        basket = await self.repo.get(basket_id)
        if not basket or basket.user_id != user_id:
            raise HTTPException(status_code=404, detail="Cesta no encontrada")
        items = await self.repo.get_items(basket_id)
        enriched = list(
            await asyncio.gather(*[self._enrich_item(item) for item in items])
        )
        prices = [i.best_offer.price for i in enriched if i.best_offer]
        total = round(sum(prices), 2) if prices else None
        return BasketDetailResponse(
            id=basket.id,
            name=basket.name,
            created_at=basket.created_at,
            updated_at=basket.updated_at,
            items=enriched,
            total_estimated=total,
        )

    async def rename_basket(
        self, basket_id: UUID, user_id: UUID, data: BasketRename
    ) -> BasketSummary:
        basket = await self.repo.get(basket_id)
        if not basket or basket.user_id != user_id:
            raise HTTPException(status_code=404, detail="Cesta no encontrada")
        basket.name = data.name
        await self.db.commit()
        await self.db.refresh(basket)
        rows = await self.repo.get_by_user(user_id)
        count = next((c for b, c in rows if b.id == basket_id), 0)
        return BasketSummary(
            id=basket.id,
            name=basket.name,
            item_count=count,
            created_at=basket.created_at,
            updated_at=basket.updated_at,
        )

    async def delete_basket(self, basket_id: UUID, user_id: UUID) -> None:
        basket = await self.repo.get(basket_id)
        if not basket or basket.user_id != user_id:
            raise HTTPException(status_code=404, detail="Cesta no encontrada")
        await self.db.delete(basket)
        await self.db.commit()

    # ── Items ──────────────────────────────────────────────────────────────────

    async def add_item(
        self, basket_id: UUID, user_id: UUID, data: BasketItemCreate
    ) -> BasketItemResponse:
        basket = await self.repo.get(basket_id)
        if not basket or basket.user_id != user_id:
            raise HTTPException(status_code=404, detail="Cesta no encontrada")
        item_count = await self.repo.count_items(basket_id)
        if item_count >= MAX_ITEMS_PER_BASKET:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Límite de {MAX_ITEMS_PER_BASKET} productos por cesta alcanzado",
            )
        item = BasketItem(
            basket_id=basket_id,
            product_name=data.product_name,
            barcode=data.barcode,
            search_query=data.search_query,
            imagen_url=data.imagen_url,
            notes=data.notes,
        )
        item = await self.repo.add_item(item)
        return await self._enrich_item(item)

    async def remove_item(
        self, basket_id: UUID, item_id: UUID, user_id: UUID
    ) -> None:
        basket = await self.repo.get(basket_id)
        if not basket or basket.user_id != user_id:
            raise HTTPException(status_code=404, detail="Cesta no encontrada")
        item = await self.repo.get_item(item_id)
        if not item or item.basket_id != basket_id:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        await self.repo.delete_item(item)

    async def clear_items(self, basket_id: UUID, user_id: UUID) -> None:
        basket = await self.repo.get(basket_id)
        if not basket or basket.user_id != user_id:
            raise HTTPException(status_code=404, detail="Cesta no encontrada")
        await self.repo.clear_items(basket_id)

    # ── Search ─────────────────────────────────────────────────────────────────

    async def search_products(
        self, query: str, user_id: UUID
    ) -> list[BasketSearchResult]:
        seen: set[str] = set()
        results: list[BasketSearchResult] = []

        # 1) Search user's own products in api_label DB
        product_repo = ProductRepository(self.db)
        own_products = await product_repo.search_by_name(user_id, query, limit=5)
        for p in own_products:
            key = p.name.lower()
            if key not in seen:
                seen.add(key)
                results.append(
                    BasketSearchResult(
                        product_name=p.name,
                        barcode=p.barcode,
                        imagen_url=p.image_url,
                        supermarket=None,
                        price=None,
                        source="mis_productos",
                    )
                )

        # 2) Search offers from api_offer
        offer_url = getattr(settings, "OFFER_API_URL", None)
        if offer_url:
            try:
                async with httpx.AsyncClient(timeout=4.0) as client:
                    resp = await client.get(
                        f"{offer_url}/api/v1/offers/compare",
                        params={"q": query, "limit": 20},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    raw_items = data if isinstance(data, list) else data.get("results", [])
            except Exception as exc:
                logger.warning("search_products offers failed: %s", exc)
                raw_items = []

            for raw in raw_items:
                name = raw.get("producto_nombre", "")
                key = name.lower()
                if name and key not in seen:
                    seen.add(key)
                    results.append(
                        BasketSearchResult(
                            product_name=name,
                            barcode=raw.get("barcode"),
                            imagen_url=raw.get("imagen_url"),
                            supermarket=raw.get("fuente"),
                            price=raw.get("precio_oferta"),
                            original_price=raw.get("precio_original"),
                            discount_percent=raw.get("descuento_porcentaje"),
                            source="ofertas",
                        )
                    )
                    if len(results) >= 10:
                        break

        return results

    # ── PDF ────────────────────────────────────────────────────────────────────

    def generate_pdf(
        self,
        basket_id: UUID,
        basket_name: str,
        username: str,
        items: list[BasketItemResponse],
    ) -> str:
        items_dicts = []
        for item in items:
            best = item.best_offer.model_dump() if item.best_offer else None
            all_offers = [o.model_dump() for o in item.all_offers]
            items_dicts.append(
                {
                    "product_name": item.product_name,
                    "barcode": item.barcode,
                    "imagen_url": item.imagen_url,
                    "best_offer": best,
                    "all_offers": all_offers,
                }
            )
        return generate_basket_pdf(str(basket_id), basket_name, username, items_dicts)

    # ── Internal helpers ───────────────────────────────────────────────────────

    async def _enrich_item(self, item: BasketItem) -> BasketItemResponse:
        offers = await self._fetch_offers(item)
        best = min(offers, key=lambda o: o.price) if offers else None

        # Resolve image: item DB → best offer → any offer → OpenFoodFacts
        imagen_url = item.imagen_url
        if not imagen_url and offers:
            for offer in offers:
                if offer.imagen_url:
                    imagen_url = offer.imagen_url
                    break
        if not imagen_url and item.barcode:
            try:
                off_product = await off_lookup_barcode(item.barcode)
                if off_product and off_product.image_url:
                    imagen_url = off_product.image_url
            except Exception:
                pass

        return BasketItemResponse(
            id=item.id,
            basket_id=item.basket_id,
            product_name=item.product_name,
            barcode=item.barcode,
            search_query=item.search_query,
            imagen_url=imagen_url,
            notes=item.notes,
            created_at=item.created_at,
            best_offer=best,
            all_offers=offers,
        )

    async def _fetch_offers(self, item: BasketItem) -> list[OfertaInfo]:
        offer_url = getattr(settings, "OFFER_API_URL", None)
        if not offer_url:
            return []
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                if item.barcode:
                    resp = await client.get(
                        f"{offer_url}/api/v1/offers/barcode/{item.barcode}"
                    )
                else:
                    query = item.search_query or item.product_name
                    resp = await client.get(
                        f"{offer_url}/api/v1/offers/compare",
                        params={"q": query, "limit": 10},
                    )
                if resp.status_code == 404:
                    return []
                resp.raise_for_status()
                data = resp.json()
                raw_items = data if isinstance(data, list) else data.get("results", [])
        except Exception as exc:
            logger.warning("_fetch_offers failed for %s: %s", item.product_name, exc)
            return []

        results: list[OfertaInfo] = []
        for raw in raw_items:
            try:
                price_val = raw.get("precio_oferta") or raw.get("precio_original") or 0
                results.append(
                    OfertaInfo(
                        supermarket=raw.get("fuente", ""),
                        product_name=raw.get("producto_nombre", item.product_name),
                        price=float(price_val),
                        original_price=raw.get("precio_original"),
                        discount_percent=raw.get("descuento_porcentaje"),
                        barcode=raw.get("barcode"),
                        imagen_url=raw.get("imagen_url"),
                        offer_url=raw.get("producto_url"),
                        scraped_at=raw.get("scraped_at"),
                    )
                )
            except Exception:
                pass
        return results
