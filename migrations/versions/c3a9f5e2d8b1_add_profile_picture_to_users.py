"""Add profile_picture to users

Revision ID: c3a9f5e2d8b1
Revises: 759d2d73edb3
Create Date: 2026-02-28 20:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3a9f5e2d8b1'
down_revision = '759d2d73edb3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('profile_picture', sa.String(length=100), nullable=True, server_default='avtar1.jpg'))


def downgrade():
    op.drop_column('users', 'profile_picture')
