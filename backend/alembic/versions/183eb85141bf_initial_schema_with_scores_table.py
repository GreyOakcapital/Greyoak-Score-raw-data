"""Initial schema with scores table

Revision ID: 183eb85141bf
Revises: 
Create Date: 2025-10-08 16:42:26.176876

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '183eb85141bf'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type for band values
    band_enum = sa.Enum('Strong Buy', 'Buy', 'Hold', 'Avoid', name='band_enum')
    band_enum.create(op.get_bind())
    
    # Create scores table
    op.create_table('scores',
        sa.Column('ticker', sa.String(length=20), nullable=False),
        sa.Column('scoring_date', sa.DateTime(), nullable=False),
        sa.Column('mode', sa.String(length=20), nullable=False),
        sa.Column('f_score', sa.Float(), nullable=True),
        sa.Column('t_score', sa.Float(), nullable=True),
        sa.Column('r_score', sa.Float(), nullable=True),
        sa.Column('o_score', sa.Float(), nullable=True),
        sa.Column('q_score', sa.Float(), nullable=True),
        sa.Column('s_score', sa.Float(), nullable=True),
        sa.Column('weighted_score', sa.Float(), nullable=True),
        sa.Column('risk_penalty', sa.Float(), nullable=True),
        sa.Column('final_score', sa.Float(), nullable=True),
        sa.Column('band', band_enum, nullable=True),
        sa.Column('guardrails', sa.String(length=500), nullable=True),
        sa.Column('as_of', sa.DateTime(), nullable=True),
        sa.Column('f_z', sa.Float(), nullable=True),
        sa.Column('t_z', sa.Float(), nullable=True),
        sa.Column('r_z', sa.Float(), nullable=True),
        sa.Column('o_z', sa.Float(), nullable=True),
        sa.Column('q_z', sa.Float(), nullable=True),
        sa.Column('s_z', sa.Float(), nullable=True),  # NOTE: s_z, not sector_z
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('ticker', 'scoring_date', 'mode'),
        sa.Index('idx_scores_ticker', 'ticker'),
        sa.Index('idx_scores_band', 'band'),
        sa.Index('idx_scores_scoring_date', 'scoring_date'),
        sa.Index('idx_scores_mode', 'mode'),
    )


def downgrade() -> None:
    # Drop table and enum
    op.drop_table('scores')
    sa.Enum('Strong Buy', 'Buy', 'Hold', 'Avoid', name='band_enum').drop(op.get_bind())
