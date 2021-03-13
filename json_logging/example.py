import argparse
import uuid

import json_logging

logger = json_logging.getLogger(__name__)


def main() -> None:
    logger.info("Message at INFO level")
    logger.debug("Message at DEBUG level")

    num_count = 99
    logger.info(
        f"Finished counting {num_count} balloons", extra={"metrics": {"num_balloons": num_count}}
    )

    with json_logging.log_stack_trace(logger):
        raise RuntimeError("example exception")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--pretty-print", action="store_true", dest="pretty")
    group.add_argument("--compact", action="store_false", dest="pretty")
    args = parser.parse_args()

    json_logging.configure_logging("DEBUG" if args.verbose else "INFO")
    json_logging.set_output_format(pretty=args.pretty)
    json_logging.update_context(request_id=uuid.uuid4().hex)

    main()
