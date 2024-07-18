import csv
import sqlite3
import logging

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_database():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS hackathons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        prizes TEXT,
        registration TEXT,
        duration TEXT,
        link TEXT,
        telegram_chat TEXT,
        comments TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

def import_hackathons(csv_file_path):
    setup_database()  # Ensure the table exists

    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    try:
        with open(csv_file_path, 'r', encoding='utf-8') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                # Skip empty rows or rows with no name
                if not row['Название']:
                    continue

                # Check if the hackathon already exists
                cursor.execute("SELECT id FROM hackathons WHERE name = ?", (row['Название'],))
                existing_hackathon = cursor.fetchone()

                if existing_hackathon:
                    # Update existing hackathon
                    cursor.execute('''
                    UPDATE hackathons
                    SET prizes = ?, registration = ?, duration = ?, link = ?, telegram_chat = ?, comments = ?
                    WHERE name = ?
                    ''', (
                        row['Призы'], row['Регистрация'], row['Длительность'],
                        row['Ссылка'], row['Telegram чат'], row['Комментарии'],
                        row['Название']
                    ))
                    logger.info(f"Updated hackathon: {row['Название']}")
                else:
                    # Insert new hackathon
                    cursor.execute('''
                    INSERT INTO hackathons (name, prizes, registration, duration, link, telegram_chat, comments)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row['Название'], row['Призы'], row['Регистрация'], row['Длительность'],
                        row['Ссылка'], row['Telegram чат'], row['Комментарии']
                    ))
                    logger.info(f"Inserted new hackathon: {row['Название']}")

        conn.commit()
        logger.info("Hackathon import completed successfully")

    except Exception as e:
        conn.rollback()
        logger.error(f"Error importing hackathons: {str(e)}")

    finally:
        conn.close()

if __name__ == '__main__':
    csv_file_path = '/home/dukhanin/com_bot/main/Community_bot/Copy of agi in 2024 - хакатоны.csv'
    import_hackathons(csv_file_path)