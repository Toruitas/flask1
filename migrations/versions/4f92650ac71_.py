"""empty message

Revision ID: 4f92650ac71
Revises: 3d24da5066a
Create Date: 2015-06-21 09:49:24.960265

"""

# revision identifiers, used by Alembic.
revision = '4f92650ac71'
down_revision = '3d24da5066a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('confirmed', sa.Boolean(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'confirmed')
    ### end Alembic commands ###
