import model
import repository

from sqlalchemy.orm import Session
from sqlalchemy import text


def test_repository_can_save_a_batch(session: Session):
    batch = model.Batch("batch1", "RUSTY-SOAPDISH", 100, eta=None)

    repo = repository.SqlRepository(session)
    repo.add(batch)
    session.commit()

    rows = session.execute(
        text('SELECT reference, sku, _purchased_quantity, eta FROM "batches"'),
    )
    assert list(rows) == [("batch1", "RUSTY-SOAPDISH", 100, None)]


def insert_order_line(session: Session):
    session.execute(
        text(
            "INSERT INTO order_lines (orderid, sku, qty) VALUES (:orderid, :sku, :qty)"
        ),
        dict(orderid="order1", sku="GENERIC-SOFA", qty=12),
    )
    [[orderline_id]] = session.execute(
        text("SELECT id FROM order_lines WHERE orderid=:orderid AND sku=:sku"),
        dict(orderid="order1", sku="GENERIC-SOFA"),
    )
    return orderline_id


def insert_batch(session: Session, batch_reference: str) -> int:
    session.execute(
        text(
            "INSERT INTO batches (reference, sku, _purchased_quantity, eta) VALUES (:batch_reference, 'GENERIC-SOFA', 100, null)"
        ),
        dict(batch_reference=batch_reference),
    )
    [[batch_id]] = session.execute(
        text(
            "SELECT id FROM batches WHERE reference=:batch_reference AND sku='GENERIC-SOFA'"
        ),
        dict(batch_reference=batch_reference),
    )
    return batch_id


def insert_allocation(session: Session, orderline_id: int, batch_id: int):
    session.execute(
        text(
            "INSERT INTO allocations (orderline_id, batch_id) VALUES (:orderline_id, :batch_id)"
        ),
        dict(
            orderline_id=orderline_id,
            batch_id=batch_id,
        ),
    )


def test_repository_can_retrieve_a_batch_with_allocations(session: Session):
    orderline_id = insert_order_line(session)
    batch1_id = insert_batch(session, "batch1")
    insert_batch(session, "batch2")
    insert_allocation(session, orderline_id, batch1_id)

    repo = repository.SqlRepository(session)
    retrieved = repo.get("batch1")

    expected = model.Batch("batch1", "GENERIC-SOFA", 100, eta=None)
    assert retrieved == expected  # Batch.__eq__ only compares reference
    assert retrieved.sku == expected.sku
    assert retrieved._purchased_quantity == expected._purchased_quantity
    assert retrieved._allocations == {
        model.OrderLine("order1", "GENERIC-SOFA", 12),
    }


def get_allocations(session: Session, batchid):
    rows = list(
        session.execute(
            text(
                "SELECT orderid"
                " FROM allocations"
                " JOIN order_lines ON allocations.orderline_id = order_lines.id"
                " JOIN batches ON allocations.batch_id = batches.id"
                " WHERE batches.reference = :batchid"
            ),
            dict(batchid=batchid),
        )
    )
    return {row[0] for row in rows}


def test_updating_a_batch(session: Session):
    order1 = model.OrderLine("order1", "WEATHERED-BENCH", 10)
    order2 = model.OrderLine("order2", "WEATHERED-BENCH", 20)
    batch = model.Batch("batch1", "WEATHERED-BENCH", 100, eta=None)
    batch.allocate(order1)

    repo = repository.SqlRepository(session)
    repo.add(batch)
    session.commit()

    batch.allocate(order2)
    repo.add(batch)
    session.commit()

    assert get_allocations(session, "batch1") == {"order1", "order2"}
