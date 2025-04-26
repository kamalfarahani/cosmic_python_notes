import abc
import model

from sqlalchemy.orm import Session
from sqlalchemy import select, insert
from db_tables import batches


class AbstractRepository(abc.ABC):
    @abc.abstractmethod
    def add(self, batch: model.Batch):
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, reference: str) -> model.Batch:
        raise NotImplementedError


class SqlRepository(AbstractRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, batch: model.Batch):
        query = insert(batches).values(
            reference=batch.reference,
            sku=batch.sku,
            _purchased_quantity=batch._purchased_quantity,
            eta=batch.eta,
        )
        self.session.execute(query)

    def get(self, reference: str) -> model.Batch:
        query = select(
            batches.c.reference,
            batches.c.sku,
            batches.c._purchased_quantity,
            batches.c.eta,
        ).where(batches.c.reference == reference)

        result = self.session.execute(query)
        row = result.fetchone()

        if not row:
            raise ValueError(f"Batch {reference} not found")

        return model.Batch(
            ref=row.reference,
            sku=row.sku,
            qty=row._purchased_quantity,
            eta=row.eta,
        )
