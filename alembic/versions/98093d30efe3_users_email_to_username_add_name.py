"""users: email to username, add name

Revision ID: 98093d30efe3
Revises: ca2ef162f6fd
Create Date: 2026-07-01 15:42:13.356488

email(EmailStr, 인증메일 전송 불필요)을 username(일반 로그인 아이디)으로 rename하고
표시용 name 컬럼을 추가한다. autogenerate가 drop+add로 제안한 것을 데이터 보존
rename(alter_column)으로 수동 교체했다.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '98093d30efe3'
down_revision: Union[str, Sequence[str], None] = 'ca2ef162f6fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'users', 'email',
        new_column_name='username',
        type_=sa.String(length=50),
        existing_type=sa.String(length=255),
    )
    op.add_column('users', sa.Column('name', sa.String(length=100), server_default='', nullable=False))
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_column('users', 'name')
    op.alter_column(
        'users', 'username',
        new_column_name='email',
        type_=sa.String(length=255),
        existing_type=sa.String(length=50),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
