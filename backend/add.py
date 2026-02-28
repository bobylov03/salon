import sqlite3

def show_database_structure(db_file):
    """Простая функция для показа структуры базы данных"""
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    print("=" * 50)
    print(f"СТРУКТУРА БАЗЫ ДАННЫХ: {db_file}")
    print("=" * 50)
    
    # Получаем все таблицы
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    for table in tables:
        table_name = table[0]
        if table_name.startswith('sqlite_'):  # Пропускаем системные
            continue
            
        print(f"\nТАБЛИЦА: {table_name}")
        print("-" * 40)
        
        # Столбцы таблицы
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        for col in columns:
            col_id, name, type_, not_null, default_val, pk = col
            print(f"  {name}: {type_} {'PRIMARY KEY' if pk else ''} {'NOT NULL' if not_null else ''}")
        
        # Количество записей
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        count = cursor.fetchone()[0]
        print(f"  Записей: {count}")
    
    conn.close()
    print("\n" + "=" * 50)

# Использование
show_database_structure("salon.db")