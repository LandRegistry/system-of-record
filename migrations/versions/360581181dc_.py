"""empty message

Revision ID: 360581181dc
Revises: 18aa913e6bb
Create Date: 2015-03-21 11:22:30.887740

"""

# revision identifiers, used by Alembic.
revision = '360581181dc'
down_revision = '18aa913e6bb'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("DROP INDEX sor_idx")
    op.execute("ALTER TABLE sor RENAME TO records")
    op.execute("ALTER TABLE records RENAME sor TO record")
    op.execute("CREATE UNIQUE INDEX title_abr_idx ON records((record->'data'->>'title_number'),(record->'data'->>'application_reference'))")

def downgrade():
    op.execute("DROP INDEX title_abr_idx")
    op.execute("ALTER TABLE records RENAME record TO sor")
    op.execute("ALTER TABLE records RENAME TO sor")
    op.execute("CREATE UNIQUE INDEX sor_idx ON sor((sor->>'sig'))")
