from relational_fraud_intelligence.settings import AppSettings


def main() -> None:
    import uvicorn

    settings = AppSettings()
    uvicorn.run(
        "relational_fraud_intelligence.app:create_app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.app_env == "local",
        factory=True,
    )


if __name__ == "__main__":
    main()
