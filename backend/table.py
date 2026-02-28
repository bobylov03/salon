import sqlite3

# Подключение к базе данных
conn = sqlite3.connect('salon.db')
cursor = conn.cursor()

try:
    # Добавляем колонку telegram_id (можно указать тип INTEGER или TEXT)
    cursor.execute("ALTER TABLE masters ADD COLUMN telegram_id INTEGER")
    
    # Если хотите добавить с значением по умолчанию:
    # cursor.execute("ALTER TABLE masters ADD COLUMN telegram_id INTEGER DEFAULT NULL")
    
    conn.commit()
    print("Колонка telegram_id успешно добавлена в таблицу masters")
    
    # Проверяем структуру таблицы
    cursor.execute("PRAGMA table_info(masters)")
    columns = cursor.fetchall()
    print("\nСтруктура таблицы masters после изменения:")
    for col in columns:
        print(f"{col[0]}: {col[1]} ({col[2]})")
        
except Exception as e:
    print(f"Ошибка: {e}")
    conn.rollback()
finally:
    conn.close()