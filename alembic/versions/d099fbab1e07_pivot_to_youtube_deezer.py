"""pivot to youtube/deezer

Revision ID: d099fbab1e07
Revises: 8886cc616b74
Create Date: 2026-06-09 19:23:53.301868

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'd099fbab1e07'
down_revision: Union[str, Sequence[str], None] = '8886cc616b74'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Spotify pivot: hosts become anonymous sessions (no OAuth tokens) and songs
    reference a generic Deezer track id plus an optional resolved YouTube video.
    Uses batch mode so SQLite handles drops/renames via table rebuild, and a
    real column rename so existing track ids survive the migration.
    """
    with op.batch_alter_table('hostsession') as batch_op:
        batch_op.add_column(sa.Column('display_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
        batch_op.drop_column('refresh_token')
        batch_op.drop_column('access_token')
        batch_op.drop_column('spotify_user_id')
        batch_op.drop_column('token_expires_at')

    with op.batch_alter_table('song') as batch_op:
        batch_op.alter_column('spotify_track_id', new_column_name='track_id')
        batch_op.add_column(sa.Column('preview_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
        batch_op.add_column(sa.Column('youtube_video_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('song') as batch_op:
        batch_op.drop_column('youtube_video_id')
        batch_op.drop_column('preview_url')
        batch_op.alter_column('track_id', new_column_name='spotify_track_id')

    # Restored NOT NULL columns need a server default for any existing rows.
    with op.batch_alter_table('hostsession') as batch_op:
        batch_op.add_column(sa.Column('token_expires_at', sa.DATETIME(), nullable=False, server_default=sa.text("'1970-01-01 00:00:00'")))
        batch_op.add_column(sa.Column('spotify_user_id', sa.VARCHAR(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('access_token', sa.VARCHAR(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('refresh_token', sa.VARCHAR(), nullable=False, server_default=''))
        batch_op.drop_column('display_name')
