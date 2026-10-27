from lib.utils.schemas import Base


class PatchInventoryRequest(Base):
    slots: list[str]
