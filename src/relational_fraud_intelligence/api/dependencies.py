from typing import cast

from fastapi import Request

from relational_fraud_intelligence.bootstrap import ApplicationContainer


def get_container(request: Request) -> ApplicationContainer:
    return cast(ApplicationContainer, request.app.state.container)
