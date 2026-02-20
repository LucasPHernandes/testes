import sqlite3
import os
from datetime import datetime, timedelta
import shutil

def fazer_backup():
    """Faz backup do banco de dados"""
    try:
        # Nome do arquivo de backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'backup_refeitorio_{timestamp}.db'
        
        # Copiar arquivo
        shutil.copy2('instance/refeitorio.db', backup_file)
        
        # Comprimir (opcional)
        import gzip
        with open(backup_file, 'rb') as f_in:
            with gzip.open(f'{backup_file}.gz', 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        os.remove(backup_file)
        
        return f'{backup_file}.gz'
    except Exception as e:
        print(f"Erro no backup: {e}")
        return None

def restaurar_backup(arquivo):
    """Restaura backup do banco de dados"""
    try:
        # Se for gzip, descomprimir
        if arquivo.endswith('.gz'):
            import gzip
            with gzip.open(arquivo, 'rb') as f_in:
                with open('instance/refeitorio.db', 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            shutil.copy2(arquivo, 'instance/refeitorio.db')
        
        return True
    except Exception as e:
        print(f"Erro na restauração: {e}")
        return False

def limpar_logs_antigos(dias=30):
    """Remove logs de auditoria mais antigos que X dias"""
    try:
        conn = sqlite3.connect('instance/refeitorio.db')
        cursor = conn.cursor()
        
        data_limite = datetime.now().date() - timedelta(days=dias)
        
        cursor.execute("""
            DELETE FROM auditoria 
            WHERE date(timestamp) < ?
        """, (data_limite,))
        
        conn.commit()
        registros_removidos = cursor.rowcount
        conn.close()
        
        return registros_removidos
    except Exception as e:
        print(f"Erro ao limpar logs: {e}")
        return 0