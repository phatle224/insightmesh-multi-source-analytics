"""Run query-run retention cleanup from cron or a one-shot container job."""

from persistence.database import SessionLocal
from services.query_retention import cleanup_expired_query_runs


def main() -> None:
    with SessionLocal() as session:
        artifacts, deleted = cleanup_expired_query_runs(session)
        session.commit()
    print(f"query retention cleanup: cleared_artifacts={artifacts} deleted_runs={deleted}")


if __name__ == "__main__":
    main()
