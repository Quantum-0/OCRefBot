import asyncio
import contextlib
import uuid

import psycopg2
import sqlalchemy as sa
from aiopg.sa import create_engine, SAConnection
from sqlalchemy.dialects.postgresql import UUID, insert as pg_insert

metadata = sa.MetaData()

tbl_users = sa.Table(
    "ocrefbot_users",
    metadata,
    sa.Column("id", sa.INTEGER, primary_key=True),
    sa.Column("username", sa.TEXT),
    sa.Column("first_name", sa.TEXT),
    sa.Column("last_name", sa.TEXT),
    sa.Column("is_premium", sa.BOOLEAN),
    sa.Column("language_code", sa.TEXT),
    sa.Column("created_at", sa.DATETIME, default=sa.func.now(), nullable=False),
    sa.Column("messages_count", sa.INTEGER, default=0, nullable=False),
)

tbl_refs = sa.Table(
    "ocrefbot_refs",
    metadata,
    sa.Column("id", UUID(True), primary_key=True, default=uuid.uuid4),
    sa.Column("user_id", None, sa.ForeignKey("ocrefbot_users.id"), nullable=False),
    sa.Column("ref_name", sa.TEXT, nullable=False),
    sa.Column("doc_file_id", sa.TEXT),
    sa.Column("photo_file_id", sa.TEXT, nullable=False),
    sa.Column("created_at", sa.DATETIME, default=sa.func.now(), nullable=False),
    sa.Column("used_at", sa.DATETIME, default=None),
    sa.Column("used_count", sa.INTEGER, default=0, nullable=False),
)


async def create_tables(conn):
    # await conn.execute("DROP TABLE IF EXISTS tbl")
    await conn.execute(
        """CREATE TABLE IF NOT EXISTS ocrefbot_users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            is_premium BOOL,
            language_code TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            messages_count INTEGER NOT NULL DEFAULT 0
        )"""
    )
    await conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    await conn.execute(
        """CREATE TABLE IF NOT EXISTS ocrefbot_refs (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id INTEGER NOT NULL REFERENCES ocrefbot_users(id) ON DELETE CASCADE,
            ref_name TEXT NOT NULL,
            doc_file_id TEXT,
            photo_file_id TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            used_at TIMESTAMP DEFAULT NULL,
            used_count INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, ref_name)
        )"""
    )


async def msg_from_user(conn: SAConnection, user_id: int, username: str, first_name: str, last_name: str, is_premium: bool, language_code: str):
    query = (
        pg_insert(tbl_users)
        .values({'id': user_id, 'username': username, 'first_name': first_name, 'last_name': last_name, 'messages_count': 1, 'is_premium': is_premium, 'language_code': language_code})
        .on_conflict_do_update(
            index_elements=('id',),
            set_={
                'messages_count': tbl_users.c.messages_count + 1,
                'username': username, 'first_name': first_name, 'last_name': last_name, 'is_premium': is_premium, 'language_code': language_code,
            }
        )
        .returning(tbl_users)
    )
    return await (await conn.execute(query)).fetchone()


class RefAlreadyExistsError(Exception):
    pass

class UserNotFoundError(Exception):
    pass

async def add_ref(conn: SAConnection, user_id: int, ref_name: str, doc_file_id: str, photo_file_id: str):
    query = (
        pg_insert(tbl_refs)
        .values(
            {
                'user_id': user_id,
                'ref_name': ref_name,
                'doc_file_id': doc_file_id,
                'photo_file_id': photo_file_id
            }
        )
        .returning(tbl_refs)
    )
    try:
        return await (await conn.execute(query)).fetchone()
    except psycopg2.errors.UniqueViolation:
        raise RefAlreadyExistsError
    except psycopg2.errors.ForeignKeyViolation:
        raise UserNotFoundError


async def get_refs(conn: SAConnection, user_id: int, filter: str | None):
    filter = filter.replace('_', '__').replace('*', '%').replace('?', '_') if filter else None
    query = (
        sa.select(tbl_refs)
        .where(tbl_refs.c.user_id == user_id)
        .order_by(sa.tuple_(tbl_refs.c.used_at, tbl_refs.c.created_at).desc())
        .limit(10)
    )
    if filter:
        query = query.where(tbl_refs.c.ref_name.ilike(f'%{filter}%'))
    return await (await conn.execute(query)).fetchall()


async def ref_sent(conn: SAConnection, ref_id: uuid.UUID):
    query = (
        sa.update(tbl_refs)
        .values(used_count=tbl_refs.c.used_count + 1, used_at=sa.func.now())
        .where(tbl_refs.c.id == ref_id)
    )
    await conn.execute(query)


async def go():
    async with db_engine() as pg:
        async with pg.acquire() as conn:
            pass
            # await create_tables(conn)
            # print(await msg_from_user(conn, 123, 'vasya', None, 'PUPKIN'))
            # print(await add_ref(conn, 123, 'my_ref', 'super_doc', 'super_photo'))
            # print(await add_ref(conn, 123, 'my_ref2', 'super_doc', 'super_photo'))
            # print(await add_ref(conn, 123, 'mysuperref3', 'super_doc', 'super_photo'))
            # print(await get_refs(conn, 123, None))
            # print(await get_refs(conn, 123, '_re'))
            # print(await get_refs(conn, 123, 'MY'))
            # print(await get_refs(conn, 123, '2'))

        # async with engine.acquire() as conn:
        #     await conn.execute(tbl.insert().values(val="abc"))
        #
        #     async for row in conn.execute(tbl.select()):
        #         print(row.id, row.val)


__engine = None


@contextlib.asynccontextmanager
async def db_engine():
    async with create_engine(
        user="postgres", database="postgres", host="localhost", password="mysecretpassword"
    ) as engine:
        yield engine


asyncio.run(go())
