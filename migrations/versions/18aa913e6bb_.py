"""empty message

Revision ID: 18aa913e6bb
Revises: 422db3d645f
Create Date: 2015-03-10 15:58:53.347920

"""

# revision identifiers, used by Alembic.
revision = '18aa913e6bb'
down_revision = '422db3d645f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    #Create unique index on table sor, use column sor and key 'sig'
    op.execute("CREATE UNIQUE INDEX sor_idx ON sor((sor->>'sig'))")
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.execute("DROP INDEX sor_idx")
    ### end Alembic commands ###