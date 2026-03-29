import sqlite3
import os

def limpiar_historial():
    db_path = os.path.join("..", "erp_system.db")
    
    if not os.path.exists(db_path):
        print("No se encontró la base de datos.")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Desactivar restricciones de llaves foráneas temporalmente
        cursor.execute("PRAGMA foreign_keys = OFF;")

        print("Limpiando tablas de ventas...")
        cursor.execute("DELETE FROM transaction_details;")
        cursor.execute("DELETE FROM transactions;")
        cursor.execute("DELETE FROM commissions_earned;")
        
        print("Limpiando historial de caja...")
        cursor.execute("DELETE FROM cash_movements;")
        cursor.execute("DELETE FROM cash_sessions;")

        # Reiniciar los contadores de ID (autoincrement)
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('transactions', 'transaction_details', 'commissions_earned', 'cash_movements', 'cash_sessions');")

        conn.commit()
        print("¡Historial de ventas y caja reiniciado exitosamente!")
        
    except Exception as e:
        print(f"Error al limpiar: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    limpiar_historial()
