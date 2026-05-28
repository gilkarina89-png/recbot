import sqlite3
from typing import List, Dict, Optional

DATABASE_PATH = "data.db"

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_recommendations INTEGER DEFAULT 0
        )
    ''')
    
    # Таблица контента (фильмы и книги)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content_type TEXT CHECK(content_type IN ('movie', 'book')),
            genre TEXT,
            mood TEXT,
            description TEXT,
            external_link TEXT
        )
    ''')
    
    # Таблица избранного
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            user_id INTEGER,
            content_id INTEGER,
            saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (content_id) REFERENCES content(id),
            PRIMARY KEY (user_id, content_id)
        )
    ''')
    
    # Заполняем тестовыми данными
    populate_sample_data(cursor)
    
    conn.commit()
    conn.close()

def populate_sample_data(cursor):
    """Заполнение базы тестовыми данными"""
    cursor.execute("SELECT COUNT(*) FROM content")
    if cursor.fetchone()[0] == 0:
        sample_content = [
            # Фильмы
            ("Дьявол носит Prada", "movie", "комедия", "весёлое", "Молодой журналистка попадает в мир высокой моды к строгой начальнице", "https://www.kinopoisk.ru/film/717/"),
            ("1+1", "movie", "драма", "вдохновляющее", "История дружбы парализованного аристократа и его сиделки из предместья", "https://www.kinopoisk.ru/film/535341/"),
            ("Начало", "movie", "фантастика", "захватывающее", "Вор, вторгающийся в сновидения, получает шанс искупить свою жизнь", "https://www.kinopoisk.ru/film/447301/"),
            ("Остров проклятых", "movie", "триллер", "загадочное", "Детективы прибывают на остров для расследования побега пациентки", "https://www.kinopoisk.ru/film/397327/"),
            ("Гарри Поттер", "movie", "фэнтези", "приключенческое", "Мальчик-волшебник поступает в школу магии и волшебства", "https://www.kinopoisk.ru/film/689/"),
            ("Мстители", "movie", "боевик", "энергичное", "Команда супергероев объединяется, чтобы спасти мир", "https://www.kinopoisk.ru/film/408038/"),
            ("Вечное сияние чистого разума", "movie", "мелодрама", "романтическое", "Пара пытается стереть друг друга из памяти", "https://www.kinopoisk.ru/film/602/"),
            
            # Книги
            ("Мастер и Маргарита", "book", "роман", "загадочное", "Мистический роман о любви, добре и зле", "https://www.litres.ru/mihail-bulgakov/master-i-margarita/"),
            ("Три товарища", "book", "роман", "романтическое", "Трагическая история любви на фоне послевоенной Германии", "https://www.litres.ru/erih-marii-remark/tri-tovarischa/"),
            ("451 градус по Фаренгейту", "book", "антиутопия", "глубокое", "Мир, где книги запрещены и сжигаются", "https://www.litres.ru/rem-bredberi/451-gradus-po-farengeytu/"),
            ("Гарри Поттер и философский камень", "book", "фэнтези", "приключенческое", "Первая книга о юном волшебнике", "https://www.litres.ru/dzhon-tolkin/vlastelin-kolec-bratstvo-kolca/"),
            ("Убить пересмешника", "book", "драма", "глубокое", "История о расовой несправедливости глазами ребёнка", "https://www.litres.ru/harper-li/ubit-peresmeshnika/"),
            ("Автостопом по галактике", "book", "юмор", "весёлое", "Невероятные приключения в космосе", "https://www.litres.ru/douglas-adams/avtostopom-po-galaktike/"),
        ]
        cursor.executemany('''
            INSERT INTO content (title, content_type, genre, mood, description, external_link)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', sample_content)

def get_user_stats(user_id: int) -> Dict:
    """Получение статистики пользователя"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT total_recommendations FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    total_recs = user[0] if user else 0
    
    cursor.execute("SELECT COUNT(*) FROM favorites WHERE user_id = ?", (user_id,))
    favorites_count = cursor.fetchone()[0]
    
    conn.close()
    return {"total_recommendations": total_recs, "favorites_count": favorites_count}

def register_user(user_id: int, username: str = None):
    """Регистрация нового пользователя"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username)
        VALUES (?, ?)
    ''', (user_id, username))
    conn.commit()
    conn.close()

def increment_recommendations(user_id: int):
    """Увеличение счётчика рекомендаций"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET total_recommendations = total_recommendations + 1 
        WHERE user_id = ?
    ''', (user_id,))
    conn.commit()
    conn.close()

def get_recommendation(content_type: str, mood: str = None, genre: str = None) -> Optional[Dict]:
    """Получение рекомендации по критериям"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    query = "SELECT id, title, content_type, genre, mood, description, external_link FROM content WHERE content_type = ?"
    params = [content_type]
    
    if mood:
        query += " AND mood = ?"
        params.append(mood)
    elif genre:
        query += " AND genre LIKE ?"
        params.append(f"%{genre}%")
    
    query += " ORDER BY RANDOM() LIMIT 1"
    
    cursor.execute(query, params)
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "id": result[0],
            "title": result[1],
            "type": result[2],
            "genre": result[3],
            "mood": result[4],
            "description": result[5],
            "link": result[6]
        }
    return None

def save_to_favorites(user_id: int, content_id: int) -> bool:
    """Сохранение в избранное"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO favorites (user_id, content_id)
            VALUES (?, ?)
        ''', (user_id, content_id))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def remove_from_favorites(user_id: int, content_id: int):
    """Удаление из избранного"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM favorites WHERE user_id = ? AND content_id = ?", (user_id, content_id))
    conn.commit()
    conn.close()

def get_favorites(user_id: int) -> List[Dict]:
    """Получение списка избранного"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.id, c.title, c.content_type, c.genre, c.description, c.external_link
        FROM favorites f
        JOIN content c ON f.content_id = c.id
        WHERE f.user_id = ?
        ORDER BY f.saved_at DESC
    ''', (user_id,))
    results = cursor.fetchall()
    conn.close()
    
    favorites = []
    for r in results:
        favorites.append({
            "id": r[0],
            "title": r[1],
            "type": r[2],
            "genre": r[3],
            "description": r[4],
            "link": r[5]
        })
    return favorites

def is_favorite(user_id: int, content_id: int) -> bool:
    """Проверка, есть ли контент в избранном"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM favorites WHERE user_id = ? AND content_id = ?", (user_id, content_id))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists