import abc
import model

from sqlalchemy.orm import Session
from sqlalchemy import select, insert
from db_tables import batches, order_lines, allocations


class AbstractRepository(abc.ABC):
    @abc.abstractmethod
    def add(self, batch: model.Batch):
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, reference: str) -> model.Batch:
        raise NotImplementedError


class SqlRepository(AbstractRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, batch: model.Batch) -> None:
        # Check if a batch with this reference already exists
        check_query = select(batches.c.id, batches.c.reference).where(
            batches.c.reference == batch.reference
        )

        batch_row = self.session.execute(check_query).fetchone()

        if not batch_row:
            query = insert(batches).values(
                reference=batch.reference,
                sku=batch.sku,
                _purchased_quantity=batch._purchased_quantity,
                eta=batch.eta,
            )
            self.session.execute(query)

        batch_row = self.session.execute(check_query).fetchone()
        batch_id = batch_row[0]  # type: ignore

        # Handle allocations
        for orderline in batch._allocations:
            # Check if orderline exists
            orderline_query = select(order_lines.c.id).where(
                order_lines.c.orderid == orderline.orderid
            )
            orderline_row = self.session.execute(orderline_query).fetchone()

            # Create orderline if it doesn't exist
            if not orderline_row:
                orderline_insert = insert(order_lines).values(
                    orderid=orderline.orderid,
                    sku=orderline.sku,
                    qty=orderline.qty,
                )
                self.session.execute(orderline_insert)
                orderline_row = self.session.execute(orderline_query).fetchone()

            orderline_id = orderline_row[0]  # type: ignore

            # Check if allocation already exists
            allocation_query = select(allocations.c.id).where(
                (allocations.c.orderline_id == orderline_id)
                & (allocations.c.batch_id == batch_id)
            )
            allocation_exists = self.session.execute(allocation_query).fetchone()

            # Create allocation if it doesn't exist
            if not allocation_exists:
                allocation_insert = insert(allocations).values(
                    orderline_id=orderline_id,
                    batch_id=batch_id,
                )
                self.session.execute(allocation_insert)

    def get(self, reference: str) -> model.Batch:
        query = select(
            batches.c.id,
            batches.c.reference,
            batches.c.sku,
            batches.c._purchased_quantity,
            batches.c.eta,
        ).where(batches.c.reference == reference)

        result = self.session.execute(query)
        row = result.fetchone()

        if not row:
            raise ValueError(f"Batch {reference} not found")

        batch = model.Batch(
            ref=row.reference,
            sku=row.sku,
            qty=row._purchased_quantity,
            eta=row.eta,
        )

        get_allocations_query = (
            select(order_lines.c.orderid, order_lines.c.sku, order_lines.c.qty)
            .select_from(allocations)
            .join(batches, batches.c.id == allocations.c.batch_id)
            .join(order_lines, allocations.c.orderline_id == order_lines.c.id)
            .where(allocations.c.batch_id == row.id)
        )

        allocation_rows = self.session.execute(get_allocations_query).fetchall()
        for allocation_row in allocation_rows:
            orderline = model.OrderLine(
                orderid=allocation_row.orderid,
                sku=allocation_row.sku,
                qty=allocation_row.qty,
            )
            batch.allocate(orderline)

        return batch
