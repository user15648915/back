"""Add studying_count and learned_count with default values

Revision ID: 5054ecfab778
Revises: 6a6f8e52f9f3
Create Date: 2025-11-25 21:11:58.491307

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '5054ecfab778'
down_revision = '6a6f8e52f9f3'
branch_labels = None
depends_on = None


def upgrade():
    # 1. ДОБАВЛЕНИЕ studying_count (временно nullable=True)
    op.add_column('users', sa.Column('studying_count', sa.Integer(), nullable=True))
    
    # 2. ЗАПОЛНЕНИЕ СУЩЕСТВУЮЩИХ ДАННЫХ (ставим 0 для старых пользователей)
    # Используем op.execute, чтобы выполнить UPDATE ДО установки NOT NULL
    op.execute(text('UPDATE users SET studying_count = 0 WHERE studying_count IS NULL'))
    
    # 3. УСТАНОВКА NOT NULL
    # Используем batch_alter_table только для alter_column, чтобы избежать реордеринга
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('studying_count', existing_type=sa.Integer(), nullable=False)
        
    # ---------- ПОВТОРЯЕМ ДЛЯ learned_count ----------
    
    # 4. ДОБАВЛЕНИЕ learned_count (временно nullable=True)
    op.add_column('users', sa.Column('learned_count', sa.Integer(), nullable=True))

    # 5. ЗАПОЛНЕНИЕ СУЩЕСТВУЮЩИХ ДАННЫХ
    op.execute(text('UPDATE users SET learned_count = 0 WHERE learned_count IS NULL'))
    
    # 6. УСТАНОВКА NOT NULL
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('learned_count', existing_type=sa.Integer(), nullable=False)


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('learned_count')
        batch_op.drop_column('studying_count')

    # ### end Alembic commands ###
