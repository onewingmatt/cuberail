"""Add notifications, user preferences, game mode

Revision ID: 8f3e1a4b2c5d
Revises: b92cd3b26844
Create Date: 2026-05-07 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers, used by Alembic.
revision: str = '8f3e1a4b2c5d'
down_revision: Union[str, Sequence[str], None] = 'b92cd3b26844'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add notification_preferences to users
    op.add_column('users', sa.Column('notification_preferences', JSONB,
                  nullable=False,
                  server_default=sa.text("'{\"game_invite\": true, \"game_started\": true, \"your_turn\": true, \"game_over\": true, \"player_joined\": true}'")))

    # Add mode to games
    op.add_column('games', sa.Column('mode', sa.String(),
                  nullable=False, server_default='async'))

    # Create notifications table
    op.create_table('notifications',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=True),
        sa.Column('type', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('body', sa.String(), nullable=True),
        sa.Column('game_id', UUID(as_uuid=True), nullable=True),
        sa.Column('read', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_table('notifications')
    op.drop_column('games', 'mode')
    op.drop_column('users', 'notification_preferences')
