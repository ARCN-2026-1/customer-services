from enum import Enum


class CustomerRole(str, Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"
