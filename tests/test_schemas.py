from datetime import datetime
from src.schemas.base import SourceMetadata
from src.schemas.startup import Startup
from src.schemas.product import Product
from src.schemas.research_paper import ResearchPaper
from src.schemas.job import Job
from src.schemas.news import News


def test_startup_schema_validation():
    source = SourceMetadata(name="TechCrunch", url="https://techcrunch.com/sample-startup")
    startup = Startup(
        name="Graphone AI",
        description="High-performance async data pipeline",
        website="https://graphone.ai",
        founding_year=2024,
        founders=["Alice Smith", "Bob Jones"],
        stage="Seed",
        total_funding="$2M",
        location="San Francisco, CA",
        categories_tags=["AI", "Data Pipeline", "Async"],
        employee_count="1-10",
        source=source,
    )

    assert startup.schemaVersion == "1.0.0"
    assert startup.recordType == "startup"
    assert startup.source.name == "TechCrunch"
    assert startup.source.url == "https://techcrunch.com/sample-startup"
    assert isinstance(startup.collectedAt, datetime)
    assert startup.name == "Graphone AI"
    assert startup.founders == ["Alice Smith", "Bob Jones"]


def test_product_schema_validation():
    source = SourceMetadata(name="ProductHunt", url="https://producthunt.com/posts/graphone")
    product = Product(
        name="Graphone Core",
        tagline="Async Ingestion Platform",
        description="Data extraction and LLM fallback engine",
        url="https://graphone.ai/product",
        maker_company="Graphone Inc.",
        launch_date="2024-05-15",
        categories_tags=["Developer Tools", "Data Processing"],
        pricing_model="Freemium",
        upvotes=450,
        source=source,
    )

    assert product.recordType == "product"
    assert product.upvotes == 450
    assert product.pricing_model == "Freemium"


def test_research_paper_schema_validation():
    source = SourceMetadata(name="arXiv", url="https://arxiv.org/abs/2401.00001")
    paper = ResearchPaper(
        title="Scalable Async Ingestion Systems",
        authors=["Dr. Jane Doe", "Prof. John Smith"],
        abstract="We present an efficient async crawling architecture...",
        published_date="2024-01-10",
        pdf_url="https://arxiv.org/pdf/2401.00001.pdf",
        journal_conference="arXiv cs.DB",
        doi="10.1234/5678",
        topics=["Data Ingestion", "Distributed Systems"],
        citations_count=12,
        source=source,
    )

    assert paper.recordType == "research_paper"
    assert paper.authors == ["Dr. Jane Doe", "Prof. John Smith"]
    assert paper.citations_count == 12


def test_job_schema_validation():
    source = SourceMetadata(name="LinkedIn", url="https://linkedin.com/jobs/view/123456")
    job = Job(
        title="Senior Python Async Engineer",
        company="Graphone AI",
        location="Remote",
        job_type="Full-time",
        salary_range="$140,000 - $180,000",
        description="Build scalable scrapers and LLM fallback chains.",
        requirements=["Python 3.11", "asyncio", "FastAPI", "Pydantic v2"],
        posted_date="2024-08-01",
        apply_url="https://graphone.ai/careers/123456",
        source=source,
    )

    assert job.recordType == "job"
    assert job.company == "Graphone AI"
    assert job.requirements == ["Python 3.11", "asyncio", "FastAPI", "Pydantic v2"]


def test_news_schema_validation():
    source = SourceMetadata(name="VentureBeat", url="https://venturebeat.com/ai/graphone-pipeline")
    news = News(
        title="Graphone Pipelines Revolutionize Async Ingestion",
        summary="A breakdown of modern python async ETL stacks.",
        content="Full body article text here...",
        author="Sarah Connor",
        published_at="2024-08-20T10:00:00Z",
        categories_tags=["AI", "Tech News"],
        sentiment_score=0.85,
        source=source,
    )

    assert news.recordType == "news"
    assert news.sentiment_score == 0.85
    assert news.author == "Sarah Connor"
