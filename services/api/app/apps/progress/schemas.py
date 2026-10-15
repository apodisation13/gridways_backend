from lib.utils.schemas import Base
from lib.utils.schemas.game import CardActionSubtype, ResourceActionSubtype
from pydantic import Field
from services.api.app.apps.cards.schemas import Deck


class UserResources(Base):
    scraps: int
    raw_bronze: int
    raw_silver: int
    raw_gold: int
    bronze_ingots: int
    silver_ingots: int
    gold_ingots: int
    crops: int
    wood: int
    silk: int
    kegs: int
    big_kegs: int
    chests: int
    keys: int
    rare_gem: int
    money: int
    flowers: int
    first_aid_kits: int
    shields: int
    immune_magics: int

    @staticmethod
    def get_one(
        row: dict,
    ) -> "UserResources":
        return UserResources(
            scraps=row["scraps"],
            raw_bronze=row["raw_bronze"],
            raw_silver=row["raw_silver"],
            raw_gold=row["raw_gold"],
            bronze_ingots=row["bronze_ingots"],
            silver_ingots=row["silver_ingots"],
            gold_ingots=row["gold_ingots"],
            crops=row["crops"],
            wood=row["wood"],
            silk=row["silk"],
            kegs=row["kegs"],
            big_kegs=row["big_kegs"],
            chests=row["chests"],
            keys=row["keys"],
            rare_gem=row["rare_gem"],
            money=row["money"],
            flowers=row["flowers"],
            first_aid_kits=row["first_aid_kits"],
            shields=row["shields"],
            immune_magics=row["immune_magics"],
        )


class UserLevel(Base):
    user_level_id: int
    finished: bool


class UserSeason(Base):
    user_season_id: int
    finished: bool
    levels: dict[int, UserLevel]


class UserCard(Base):
    user_card_id: int
    count: int


class UserLeader(Base):
    user_leader_id: int
    count: int


class UserDeck(Base):
    user_deck_id: int
    deck: Deck


class UserProgressResponse(Base):
    user_resources: UserResources
    user_cards: dict[int, UserCard]
    user_leaders: dict[int, UserLeader]
    user_decks: list[UserDeck]
    user_seasons: dict[int, UserSeason]


class CreateDeckRequest(Base):
    deck_name: str = Field(
        ...,
        min_length=3,
        max_length=50,
    )
    leader_id: int
    cards: list[int]


class ListDecksResponse(Base):
    decks: list[UserDeck]


class ResourcesRequest(Base):
    subtype: ResourceActionSubtype
    data: dict


class CardCraftMillRequest(Base):
    subtype: CardActionSubtype
    recipe: dict | None = None


class CardCraftMillResponse(Base):
    cards: dict[int, UserCard] | dict[int, UserLeader]
    resources: UserResources


class OpenRelatedLevelsResponse(Base):
    seasons: dict[int, UserSeason]


class CardCraftBonusRequest(Base):
    cards_ids: list[int]


class CardCraftBonusResponse(Base):
    cards: dict[int, UserCard]
