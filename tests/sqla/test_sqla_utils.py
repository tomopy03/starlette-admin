import enum
import ipaddress
import uuid

import arrow
import pytest
import pytest_asyncio
from colour import Color
from httpx import AsyncClient
from sqlalchemy import Column, Integer, MetaData, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base
from sqlalchemy_utils import (
    ArrowType,
    ChoiceType,
    ColorType,
    Country,
    CountryType,
    EmailType,
    IPAddressType,
    URLType,
    UUIDType,
)
from starlette.applications import Starlette
from starlette_admin import ColorField, EmailField, EnumField, StringField, URLField
from starlette_admin.contrib.sqla import Admin, ModelView
from starlette_admin.contrib.sqla.fields import ArrowField
from starlette_admin.fields import CountryField

from tests.sqla.utils import get_test_engine

pytestmark = pytest.mark.asyncio


Base = declarative_base(metadata=MetaData())


class Counter(str, enum.Enum):
    ONE = "one"
    TWO = "two"


class Model(Base):
    __tablename__ = "model"

    uuid = Column(UUIDType(binary=False), primary_key=True, default=uuid.uuid4)
    choice = Column(ChoiceType([(1, "One"), (2, "Two")], impl=Integer()))
    counter = Column(ChoiceType(Counter))
    arrow = Column(ArrowType, default=arrow.utcnow())
    url = Column(URLType)
    email = Column(EmailType)
    ip_address = Column(IPAddressType)
    country = Column(CountryType)
    color = Column(ColorType)
    # Remove due to https://github.com/MagicStack/asyncpg/issues/991
    # balance = Column(
    #     CompositeType(
    #         "money_type", [Column("currency", CurrencyType), Column("amount", Integer)]
    #     )
    # )


async def test_model_fields_conversion():
    assert ModelView(Model).fields == [
        StringField("uuid", exclude_from_create=True, exclude_from_edit=True),
        EnumField("choice", choices=((1, "One"), (2, "Two")), coerce=int),
        EnumField("counter", enum=Counter, coerce=str),
        ArrowField("arrow"),
        URLField("url"),
        EmailField("email"),
        StringField("ip_address"),
        CountryField("country"),
        ColorField("color"),
        # CollectionField(
        #     "balance",
        #     fields=[
        #         CurrencyField("currency", searchable=False, orderable=False),
        #         IntegerField("amount", searchable=False, orderable=False),
        #     ],
        # ),
    ]


@pytest.fixture
def engine(fake_image) -> Engine:
    _engine = get_test_engine()
    Base.metadata.create_all(_engine)
    yield _engine
    Base.metadata.drop_all(_engine)


@pytest.fixture
def session(engine: Engine) -> Session:
    with Session(engine) as session:
        yield session


@pytest_asyncio.fixture
async def client(engine: Engine):
    admin = Admin(engine)
    admin.add_view(ModelView(Model))
    app = Starlette()
    admin.mount_to(app)
    async with AsyncClient(app=app, base_url="http://testserver") as c:
        yield c


async def test_create(client: AsyncClient, session: Session):
    response = await client.post(
        "/admin/model/create",
        data={
            "choice": "1",
            "counter": "one",
            "arrow": "2023-01-06T16:12:16.221904+00:00",
            "url": "https://example.com",
            "email": "admin@example.com",
            "ip_address": "192.123.45.55",
            "country": "BJ",
            "color": "#fde",
            # "balance.currency": "XOF",
            # "balance.amount": "1000000",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    stmt = select(Model).where(Model.email == "admin@example.com")
    model = session.execute(stmt).scalar_one()
    assert model is not None
    assert model.choice == 1
    assert model.counter == Counter("one")
    assert model.arrow == arrow.get("2023-01-06T16:12:16.221904+00:00")
    assert model.url == "https://example.com"
    assert model.email == "admin@example.com"
    assert model.ip_address == ipaddress.ip_address("192.123.45.55")
    assert model.country == Country("BJ")
    assert model.color == Color("#fde")
    # assert model.balance.currency == Currency("XOF")
    # assert model.balance.amount == 1000000

    response = await client.get(f"/admin/model/detail/{model.uuid}")
    assert response.status_code == 200


async def test_get_detail(client: AsyncClient, session: Session):
    pass
