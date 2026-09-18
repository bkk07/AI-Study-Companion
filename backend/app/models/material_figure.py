import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDTimestampMixin

# Vision-assigned figure kinds (see vision_service.FIGURE_TYPES).
FIGURE_TYPES = frozenset({"CHART", "TABLE_SCAN", "DIAGRAM", "PHOTO", "DECORATIVE", "UNKNOWN"})


class MaterialFigure(Base, UUIDTimestampMixin):
    """One extracted figure: image bytes on the shared volume, text twin in DB.

    The PNG lives at storage_path (thumbnail at thumb_path); summary,
    markdown_table (charts), and latex_table (table scans) are the searchable
    twin that flows into chunks/RAG/tutor citations. Rows are replaced per
    material on re-extraction (same idempotency as chunks), keyed by
    (material_id, page_number, fig_index).
    """

    __tablename__ = "material_figures"
    __table_args__ = (
        UniqueConstraint(
            "material_id", "page_number", "fig_index", name="uq_figures_material_page_idx"
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    fig_index: Mapped[int] = mapped_column(Integer, nullable=False)
    figure_type: Mapped[str] = mapped_column(String(16), nullable=False, server_default="DIAGRAM")
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    thumb_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    image_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    markdown_table: Mapped[str | None] = mapped_column(Text, nullable=True)
    latex_table: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    vision_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
