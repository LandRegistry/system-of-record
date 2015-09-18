"""empty message

Revision ID: 3fcddd64a72
Revises: 360581181dc
Create Date: 2015-09-18 10:46:03.631898

"""

# revision identifiers, used by Alembic.
revision = '3fcddd64a72'
down_revision = '360581181dc'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('records', sa.Column('created_date', sa.DateTime(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('records', 'created_date')
    ### end Alembic commands ###