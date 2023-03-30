"""better

Revision ID: c18a5b531790
Revises: 1bb7dc8d7098
Create Date: 2022-04-10 06:25:49.799968

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c18a5b531790'
down_revision = '1bb7dc8d7098'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('companies_basic', 'length')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('companies_basic', sa.Column('length', sa.VARCHAR(length=64), nullable=True))
    # ### end Alembic commands ###