import sqlite3
import pandas as pd
from tabulate import tabulate

def explore_database(db_path='backend/salon.db'):
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("=" * 60)
        print(f"Исследование базы данных: {db_path}")
        print("=" * 60)
        
        # 1. Получаем список всех таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("В базе данных нет таблиц.")
            return
        
        print(f"\nНайдено таблиц: {len(tables)}")
        print("Список таблиц:")
        for i, table in enumerate(tables, 1):
            print(f"{i}. {table[0]}")
        
        print("\n" + "=" * 60)
        
        # 2. Для каждой таблицы показываем структуру и данные
        for table_name in [table[0] for table in tables]:
            print(f"\n\nТАБЛИЦА: {table_name}")
            print("-" * 40)
            
            # Получаем информацию о столбцах таблицы
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns_info = cursor.fetchall()
            
            print("Структура таблицы:")
            column_names = []
            for col in columns_info:
                col_id, name, col_type, notnull, default_value, pk = col
                column_names.append(name)
                print(f"  {name} ({col_type}){' PRIMARY KEY' if pk else ''}{' NOT NULL' if notnull else ''}")
            
            # Получаем данные из таблицы
            cursor.execute(f"SELECT * FROM {table_name};")
            rows = cursor.fetchall()
            
            print(f"\nКоличество записей: {len(rows)}")
            
            if rows:
                print("\nСодержимое таблицы:")
                # Используем pandas для красивого отображения
                df = pd.DataFrame(rows, columns=column_names)
                print(tabulate(df, headers='keys', tablefmt='grid', showindex=False))
            
            print("-" * 40)
        
        # 3. Дополнительная информация о связях таблиц
        print("\n" + "=" * 60)
        print("ИНФОРМАЦИЯ О ВНЕШНИХ КЛЮЧАХ:")
        
        for table_name in [table[0] for table in tables]:
            cursor.execute(f"PRAGMA foreign_key_list({table_name});")
            foreign_keys = cursor.fetchall()
            
            if foreign_keys:
                print(f"\nТаблица '{table_name}':")
                for fk in foreign_keys:
                    print(f"  → Связь с таблицей '{fk[2]}' (столбец: {fk[3]} → {fk[4]})")
        
        # 4. Выполняем несколько полезных запросов
        print("\n" + "=" * 60)
        print("АНАЛИТИЧЕСКИЕ ЗАПРОСЫ:")
        
        # Проверяем наличие типичных таблиц для салона красоты
        typical_tables = ['clients', 'services', 'appointments', 'employees', 'products']
        
        for table in typical_tables:
            if table in [t[0] for t in tables]:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  • Таблица '{table}': {count} записей")
        
        # Закрываем соединение
        conn.close()
        
        print("\n" + "=" * 60)
        print("Исследование завершено!")
        
    except sqlite3.Error as e:
        print(f"Ошибка при работе с базой данных: {e}")
    except FileNotFoundError:
        print(f"Файл базы данных '{db_path}' не найден!")
    except Exception as e:
        print(f"Произошла ошибка: {e}")

# Альтернативная функция для простого просмотра
def simple_view(db_path='backend/salon.db'):
    """Простой просмотр данных без дополнительных библиотек"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем список таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = cursor.fetchall()
        
        print(f"База данных: {db_path}")
        print(f"Количество таблиц: {len(tables)}\n")
        
        for table in tables:
            table_name = table[0]
            print(f"Таблица: {table_name}")
            print("-" * 40)
            
            # Получаем структуру
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            # Получаем данные
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 10")
            rows = cursor.fetchall()
            
            # Выводим названия столбцов
            col_names = [col[1] for col in columns]
            print("Столбцы:", ", ".join(col_names))
            
            # Выводим первые несколько строк
            if rows:
                print("\nПервые 10 записей:")
                for row in rows:
                    print(row)
            else:
                print("\nТаблица пуста")
            
            # Общее количество записей
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total = cursor.fetchone()[0]
            print(f"\nВсего записей: {total}")
            print("=" * 40 + "\n")
        
        conn.close()
        
    except Exception as e:
        print(f"Ошибка: {e}")

# Функция для экспорта в Excel
def export_to_excel(db_path='backend/salon.db', output_file='backend/salon_data.xlsx'):
    """Экспорт всех таблиц в Excel файл"""
    try:
        conn = sqlite3.connect(db_path)
        
        # Получаем список таблиц
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [table[0] for table in cursor.fetchall()]
        
        # Создаем Excel writer
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            for table in tables:
                df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
                df.to_excel(writer, sheet_name=table[:31], index=False)  # Ограничение в 31 символ для имени листа
        
        conn.close()
        print(f"Данные успешно экспортированы в файл: {output_file}")
        
    except Exception as e:
        print(f"Ошибка при экспорте: {e}")

if __name__ == "__main__":
    # Выберите один из вариантов:
    
    # Вариант 1: Полный анализ базы данных
    print("ВАРИАНТ 1: Полный анализ базы данных")
    explore_database('backend/salon.db')
    
    # Вариант 2: Простой просмотр (раскомментировать при необходимости)
    # print("\n\nВАРИАНТ 2: Простой просмотр")
    # simple_view('backend/salon.db')
    
    # Вариант 3: Экспорт в Excel (раскомментировать при необходимости)
    # print("\n\nВАРИАНТ 3: Экспорт в Excel")
    # export_to_excel('backend/salon.db', 'backend/salon_export.xlsx')