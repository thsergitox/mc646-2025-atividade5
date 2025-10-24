# tests/test_fraud_detection_system.py

import pytest
from datetime import datetime, timedelta
from src.fraud.FraudDetectionSystem import FraudDetectionSystem
from src.fraud.Transaction import Transaction
from src.fraud.FraudCheckResult import FraudCheckResult

# Classe que agrupa todos os testes para o sistema de detecção de fraude
class TestFraudDetectionSystem:

    def setup_method(self):
        """
        Este método é executado antes de cada teste, garantindo que cada um 
        comece com uma nova instância do sistema.
        """
        self.system = FraudDetectionSystem()
        self.now = datetime.now()

    def test_caso_1_valor_elevado(self):
        """
        Testa a regra de fraude para transações com valor superior a 10.000.
        """
        # Parâmetros
        current_transaction = Transaction(
            amount=15000.00,
            timestamp=self.now,
            location="Brasil"
        )
        previous_transactions = []
        blacklisted_locations = []

        # Execução e Verificação
        result = self.system.check_for_fraud(current_transaction, previous_transactions, blacklisted_locations)

        assert result.is_fraudulent is True
        assert result.verification_required is True
        assert result.is_blocked is False
        assert result.risk_score == 50

    def test_caso_2_transacoes_excessivas(self):
        """
        Testa a regra de bloqueio por mais de 10 transações na última hora.
        O teste é configurado com 11 transações recentes para ativar a regra.
        """
        # Parâmetros
        current_transaction = Transaction(
            amount=500.00,
            timestamp=self.now,
            location="Brasil"
        )
        # Cria 11 transações nos últimos 59 minutos
        previous_transactions = [
            Transaction( 50.0, self.now - timedelta(minutes=i*5), "Brasil") for i in range(1, 12)
        ]
        # Adiciona uma transação antiga que não deve ser contada
        previous_transactions.append(
            Transaction(100.0, self.now - timedelta(minutes=601), "Brasil")
        )
        blacklisted_locations = []

        # Execução e Verificação
        result = self.system.check_for_fraud(current_transaction, previous_transactions, blacklisted_locations)

        assert result.is_blocked is True
        assert result.risk_score == 30
        # A regra de transações excessivas por si só não marca como fraude
        assert result.is_fraudulent is False 
        
    def test_caso_3_localizacao_recente_sem_fraude(self):
        """
        Testa o cenário onde há uma transação recente (< 30 min), mas na mesma localização,
        o que não deve ser considerado fraude.
        """
        # Parâmetros
        current_transaction = Transaction(
            amount=500.00,
            timestamp=self.now,
            location="Brasil"
        )
        previous_transactions = [
            Transaction(
                amount=200.00,
                timestamp=self.now - timedelta(minutes=15),
                location="Brasil"
            )
        ]
        blacklisted_locations = []

        # Execução e Verificação
        result = self.system.check_for_fraud(current_transaction, previous_transactions, blacklisted_locations)

        assert result.is_fraudulent is False
        assert result.is_blocked is False
        assert result.verification_required is False
        assert result.risk_score == 0

    def test_caso_4_mudanca_rapida_localizacao(self):
        """
        Testa a regra de fraude por mudança rápida de localização (transação em
        local diferente em menos de 30 minutos).
        """
        # Parâmetros
        current_transaction = Transaction(
            amount=500.00,
            timestamp=self.now,
            location="Brasil"
        )
        previous_transactions = [
            Transaction(
                amount=200.00,
                timestamp=self.now - timedelta(minutes=15),
                location="EUA"
            )
        ]
        blacklisted_locations = []

        # Execução e Verificação
        result = self.system.check_for_fraud(current_transaction, previous_transactions, blacklisted_locations)

        assert result.is_fraudulent is True
        assert result.verification_required is True
        assert result.is_blocked is False
        assert result.risk_score == 20

    def test_caso_5_localizacao_em_blacklist(self):
        """
        Testa a regra de bloqueio imediato e score máximo para transações em
        locais na lista de restrição.
        """
        # Parâmetros
        current_transaction = Transaction(
            amount=500.00,
            timestamp=self.now,
            location="Brasil"
        )
        previous_transactions = []
        blacklisted_locations = ["Brasil", "País de Alto Risco"]

        # Execução e Verificação
        result = self.system.check_for_fraud(current_transaction, previous_transactions, blacklisted_locations)

        assert result.is_blocked is True
        assert result.risk_score == 100
        # A regra da blacklist por si só não marca como fraude, apenas bloqueia
        assert result.is_fraudulent is False

    def test_limit_not_fraud_amount(self):
        """
        Mata o Mutante 133 (>= 10000).
        O original (>) não deve marcar 10.000 como fraude.
        O mutante (>=) irá marcar como fraude.
        """
        current_transaction = Transaction(
            amount=10000.00,
            timestamp=self.now,
            location="Brasil"
        )
        result = self.system.check_for_fraud(current_transaction, [], self.blacklisted_locations)
        
        # Original deve ser False. Mutante será True.
        assert result.is_fraudulent is False
        assert result.risk_score == 0

    def test_limit_fraud_amount(self):
        """
        Mata o Mutante 134 (> 10001).
        O original (> 10000) deve marcar 10.001 como fraude.
        O mutante (> 10001) não irá marcar.
        """
        current_transaction = Transaction(
            amount=10001.00,
            timestamp=self.now,
            location="Brasil"
        )
        result = self.system.check_for_fraud(current_transaction, [], self.blacklisted_locations)
        
        # Original deve ser True. Mutante será False.
        assert result.is_fraudulent is True
        assert result.risk_score == 50

    def test_previous_transaction_equals_10(self):
        """
        Mata Mutante 142 (count=1) e Mutante 154 (>= 10).
        Com 10 transações:
        - Original (> 10) não bloqueia (10 > 10 é Falso).
        - Mutante 142 (count=1) conta 11 e bloqueia (11 > 10 é Verdadeiro).
        - Mutante 154 (>= 10) bloqueia (10 >= 10 é Verdadeiro).
        """
        current_transaction = Transaction(500.0, self.now, "Brasil")
        previous_transactions = [
            Transaction(50.0, self.now - timedelta(minutes=10), "Brasil") for _ in range(10)
        ]
        
        result = self.system.check_for_fraud(current_transaction, previous_transactions, self.blacklisted_locations)
        
        # Original não bloqueia. Mutantes 142 e 154 bloqueiam.
        assert result.is_blocked is False

    def test_count_ignore_tx_outside_60_min(self):
        """
        Mata Mutante 147 (.../61).
        Usa 10 tx recentes + 1 tx de 60.5 minutos atrás.
         Original (.../60) não conta a tx de 60.5 min (total 10). Não bloqueia.
        - Mutante (.../61) conta a tx (3630/61 = 59.5), (total 11). Bloqueia.
        """
        current_transaction = Transaction(500.0, self.now, "Brasil")
        # 10 transações recentes
        previous_transactions = [
            Transaction(50.0, self.now - timedelta(minutes=10), "Brasil") for _ in range(10)
        ]
        # 1 transação de 60.5 minutos (3630 segundos)
        previous_transactions.append(
            Transaction(50.0, self.now - timedelta(minutes=60, seconds=30), "Brasil")
        )
        
        result = self.system.check_for_fraud(current_transaction, previous_transactions, self.blacklisted_locations)
        
        # Original (10 tx) não bloqueia. Mutante (11 tx) bloqueia.
        assert result.is_blocked is False

    def test_count_include_tx_equals_60_min(self):
        """
        Mata Mutante 149 (< 60).
        Usa 11 transações exatamente de 60 minutos atrás.
        - Original (<= 60) conta todas (total 11). Bloqueia.
        - Mutante (< 60) não conta nenhuma (total 0). Não bloqueia.
        """
        current_transaction = Transaction(500.0, self.now, "Brasil")
        previous_transactions = [
            Transaction(50.0, self.now - timedelta(minutes=60), "Brasil") for _ in range(11)
        ]
        
        result = self.system.check_for_fraud(current_transaction, previous_transactions, self.blacklisted_locations)
        
        # Original (11 tx) bloqueia. Mutante (0 tx) não bloqueia.
        assert result.is_blocked is True

    def test_count_ignore_tx_equals_61_min(self):
        """
        Mata Mutante 150 (<= 61).
        Usa 11 transações de 61 minutos atrás.
        - Original (<= 60) não conta nenhuma (total 0). Não bloqueia.
        - Mutante (<= 61) conta todas (total 11). Bloqueia.
        """
        current_transaction = Transaction(500.0, self.now, "Brasil")
        previous_transactions = [
            Transaction(50.0, self.now - timedelta(minutes=61), "Brasil") for _ in range(11)
        ]
        
        result = self.system.check_for_fraud(current_transaction, previous_transactions, self.blacklisted_locations)

        # Original (0 tx) não bloqueia. Mutante (11 tx) bloqueia.
        assert result.is_blocked is False

    def test_count_6_tx_not_blocked(self):
        """
        Mata Mutante 153 (+= 2).
        Usa 6 transações recentes.
        - Original (+= 1) conta 6. Não bloqueia.
        - Mutante (+= 2) conta 12. Bloqueia.
        """
        current_transaction = Transaction(500.0, self.now, "Brasil")
        previous_transactions = [
            Transaction(50.0, self.now - timedelta(minutes=10), "Brasil") for _ in range(6)
        ]
        
        result = self.system.check_for_fraud(current_transaction, previous_transactions, self.blacklisted_locations)
        
        # Original (6 tx) não bloqueia. Mutante (12 tx) bloqueia.
        assert result.is_blocked is False

    def test_score_sum_rule1_and_rule2(self):
        """
        Mata Mutante 158 (risk_score = 30).
        Combina Regra 1 (Valor > 10k, score=50) e Regra 2 (Contagem > 10, score+=30).
        - Original: risk_score = 50 + 30 = 80.
        - Mutante: risk_score = 50, depois risk_score = 30. (Resultado 30).
        """
        current_transaction = Transaction(15000.0, self.now, "Brasil") # Regra 1
        previous_transactions = [
            Transaction(50.0, self.now - timedelta(minutes=10), "Brasil") for _ in range(11) # Regra 2
        ]
        
        result = self.system.check_for_fraud(current_transaction, previous_transactions, self.blacklisted_locations)
        
        assert result.is_fraudulent is True
        assert result.is_blocked is True
        # Original == 80. Mutante == 30.
        assert result.risk_score == 80

    def test_location_ignore_change_at_30_1_min(self):
        """
        Mata Mutante 167 (local .../61).
        Usa 1 tx em local diferente há 30.1 minutos (1806 seg).
        - Original (.../60): 1806/60 = 30.1. (30.1 < 30 é Falso). Não é fraude.
        - Mutante (.../61): 1806/61 = 29.6. (29.6 < 30 é Verdadeiro). É fraude.
        """
        current_transaction = Transaction(500.0, self.now, "Brasil")
        previous_transactions = [
            Transaction(100.0, self.now - timedelta(minutes=30, seconds=6), "EUA")
        ]
        
        result = self.system.check_for_fraud(current_transaction, previous_transactions, self.blacklisted_locations)
        
        # Original não é fraude. Mutante é fraude.
        assert result.is_fraudulent is False
        assert result.risk_score == 0

    def test_location_ignore_change_equals_30_min(self):
        """
        Mata Mutante 169 (local <= 30).
        Usa 1 tx em local diferente há exatamente 30 minutos.
        - Original (< 30): (30.0 < 30 é Falso). Não é fraude.
        - Mutante (<= 30): (30.0 <= 30 é Verdadeiro). É fraude.
        """
        current_transaction = Transaction(500.0, self.now, "Brasil")
        previous_transactions = [
            Transaction(100.0, self.now - timedelta(minutes=30), "EUA")
        ]
        
        result = self.system.check_for_fraud(current_transaction, previous_transactions, self.blacklisted_locations)
        
        # Original não é fraude. Mutante é fraude.
        assert result.is_fraudulent is False
        assert result.risk_score == 0

    def test_location_ignore_change_at_30_5_min(self):
        """
        Mata Mutante 170 (local < 31).
        Usa 1 tx em local diferente há 30.5 minutos.
        - Original (< 30): (30.5 < 30 é Falso). Não é fraude.
        - Mutante (< 31): (30.5 < 31 é Verdadeiro). É fraude.
        """
        current_transaction = Transaction(500.0, self.now, "Brasil")
        previous_transactions = [
            Transaction(100.0, self.now - timedelta(minutes=30, seconds=30), "EUA")
        ]
        
        result = self.system.check_for_fraud(current_transaction, previous_transactions, self.blacklisted_locations)
        
        # Original não é fraude. Mutante é fraude.
        assert result.is_fraudulent is False
        assert result.risk_score == 0

    def test_score_sum_rule1_and_rule3(self):
        """
        Mata Mutante 177 (risk_score = 20).
        Combina Regra 1 (Valor > 10k, score=50) e Regra 3 (Local, score+=20).
        - Original: risk_score = 50 + 20 = 70.
        - Mutante: risk_score = 50, depois risk_score = 20. (Resultado 20).
        """
        current_transaction = Transaction(15000.0, self.now, "Brasil") # Regra 1
        previous_transactions = [
            Transaction(100.0, self.now - timedelta(minutes=15), "EUA") # Regra 3
        ]
        
        result = self.system.check_for_fraud(current_transaction, previous_transactions, self.blacklisted_locations)
        
        assert result.is_fraudulent is True
        # Original == 70. Mutante == 20.
        assert result.risk_score == 70

