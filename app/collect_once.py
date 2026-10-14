import logging

from app.infrastructure.collect_job import CollectIndexPricesJob
from app.infrastructure.config import Settings

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    payload = CollectIndexPricesJob(Settings.from_env()).execute()
    logger.info("Initial collection finished: %s", payload)


if __name__ == "__main__":
    main()
