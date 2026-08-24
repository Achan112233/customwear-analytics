from app.database import SessionLocal
from app.models import AnalyticsJob, JobStatus
from app.services.segmentation import run_segmentation


def execute_segmentation(job_id: str) -> int:
    with SessionLocal() as db:
        job = db.get(AnalyticsJob, job_id)
        if job is None:
            raise ValueError(f"Unknown analytics job: {job_id}")
        try:
            job.status = JobStatus.running
            db.commit()
            run = run_segmentation(db)
            job.status = JobStatus.completed
            job.result_run_id = run.id
            db.commit()
            return run.id
        except Exception as exc:
            db.rollback()
            job = db.get(AnalyticsJob, job_id)
            job.status = JobStatus.failed
            job.error = str(exc)[:500]
            db.commit()
            raise
