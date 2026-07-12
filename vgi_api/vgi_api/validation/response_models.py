from typing import List
from pydantic import BaseModel


class LVNetworks(BaseModel):

    networks: List[int]
