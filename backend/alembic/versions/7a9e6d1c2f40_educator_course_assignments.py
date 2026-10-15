"""Add explicit educator-to-course assignments for scoped analytics."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "7a9e6d1c2f40"
down_revision: Union[str, None] = "3f30de13040c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "educator_course_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("educator_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["educator_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("educator_id", "course_id", name="uq_educator_course_assignment"),
    )
    with op.batch_alter_table("educator_course_assignments") as batch_op:
        batch_op.create_index("ix_educator_course_assignments_id", ["id"], unique=False)
        batch_op.create_index("ix_educator_course_assignments_educator_id", ["educator_id"], unique=False)
        batch_op.create_index("ix_educator_course_assignments_course_id", ["course_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("educator_course_assignments") as batch_op:
        batch_op.drop_index("ix_educator_course_assignments_course_id")
        batch_op.drop_index("ix_educator_course_assignments_educator_id")
        batch_op.drop_index("ix_educator_course_assignments_id")
    op.drop_table("educator_course_assignments")
