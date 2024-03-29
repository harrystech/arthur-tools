import argparse
import uuid
from datetime import datetime, timezone

import json_logging

logger = json_logging.getLogger(__name__)


def main() -> None:
    logger.info("Message at INFO level")
    logger.debug("Message at DEBUG level")

    num_count = 99
    logger.warning(
        f"Finished counting {num_count} balloons", extra={"metrics": {"num_balloons": num_count}}
    )
    # The date in the extra field will be in ISO 8601 (with 'T' separator and timzeone).
    now = datetime.now(timezone.utc)
    logger.info("Started now at: %s (using default __str__())", now, extra={"utcnow": now})

    with json_logging.log_stack_trace(logger):
        raise RuntimeError("example exception")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    verbose_group = parser.add_mutually_exclusive_group()
    verbose_group.add_argument("--verbose", action="store_true", dest="verbose")
    verbose_group.add_argument("--terse", action="store_false", dest="verbose")
    pretty_group = parser.add_mutually_exclusive_group()
    pretty_group.add_argument("--pretty-print", action="store_true", dest="pretty")
    pretty_group.add_argument("--compact", action="store_false", dest="pretty")
    args = parser.parse_args()

    json_logging.configure_logging("DEBUG" if args.verbose else "INFO")
    json_logging.set_output_format(pretty=args.pretty, terse=not args.verbose)
    json_logging.update_context(request_id=uuid.uuid4().hex)

    main()
