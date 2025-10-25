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

    def test_limit_amount_10k_and_count_10(self):
        """
        Mata:
        - M133 (amount >= 10000) -> Daria fraude
        - M142 (count = 1) -> Contaria 11, daria bloqueio
        - M154 (count >= 10) -> Daria bloqueio
        
        Teste: Valor exatamente no limite (10000) e contagem exatamente no limite (10).
        Original: Não é fraude (só > 10k), não bloqueia (só > 10).
        """
        current_transaction = Transaction(10000.00, self.now, "Brasil")
        previous_transactions = [
            Transaction(50.0, self.now - timedelta(minutes=10), "Brasil") for _ in range(10)
        ]

        blacklisted_locations = []
        
        result = self.system.check_for_fraud(current_transaction, previous_transactions, blacklisted_locations)
        
        assert result.is_fraudulent is False
        assert result.is_blocked is False
        assert result.risk_score == 0

    def test_limit_amount_10001_and_count_6(self):
        """
        Mata:
        - M134 (amount > 10001) -> Não daria fraude
        - M153 (count += 2) -> Contaria 12, daria bloqueio
        
        Teste: Valor logo acima do limite (10001) e contagem baixa (6).
        Original: É fraude (score=50), não bloqueia (6 tx).
        """
        current_transaction = Transaction(10001.00, self.now, "Brasil")
        previous_transactions = [
            Transaction(50.0, self.now - timedelta(minutes=10), "Brasil") for _ in range(6)
        ]

        blacklisted_locations = []

        result = self.system.check_for_fraud(current_transaction, previous_transactions, blacklisted_locations)
        
        assert result.is_fraudulent is True
        assert result.is_blocked is False
        assert result.risk_score == 50

    def test_score_sum_all_rules_active(self):
        """
        Combina as 3 regras que somam score.
        O sistema atual só considera a última transação
        para a verificação de mudança de localização (R3),
        portanto, o score final esperado é 80 (R1 + R2).
        """
        current_transaction = Transaction(15000.0, self.now, "Brasil")  # R1
        previous_transactions = [
            Transaction(100.0, self.now - timedelta(minutes=15), "EUA")
        ]
        previous_transactions.extend(
            [Transaction(50.0, self.now - timedelta(minutes=20), "Brasil") for _ in range(10)]
        )

        blacklisted_locations = []

        result = self.system.check_for_fraud(current_transaction, previous_transactions, blacklisted_locations)

        assert result.is_fraudulent is True
        assert result.is_blocked is True
        assert result.risk_score == 80  # R1 (50) + R2 (30)


    def test_limit_time_exact_60_and_30_min(self):
        """
        Mata:
        - M149 (R2: < 60) -> Não contaria as 11 txs, não bloquearia
        - M169 (R3: <= 30) -> Marcaria fraude
        
        Teste: Limites exatos de tempo. 11 txs @ 60 min e 1 tx @ 30 min (loc diferente).
        Original: R2 conta (<= 60), R3 não conta (< 30).
        """
        current_transaction = Transaction(500.0, self.now, "Brasil")
        previous_transactions = [
            # R3: Exatamente 30 min, local diferente
            Transaction(100.0, self.now - timedelta(minutes=30), "EUA")
        ]
        # R2: Exatamente 60 min, 10 txs (total 11 com a de cima)
        previous_transactions.extend(
            [Transaction(50.0, self.now - timedelta(minutes=60), "Brasil") for _ in range(10)]
        )

        blacklisted_locations = []

        result = self.system.check_for_fraud(current_transaction, previous_transactions, blacklisted_locations)

        # Original: R2 (Bloqueia), R3 (Não é fraude)
        assert result.is_blocked is True
        assert result.is_fraudulent is False # A fraude da R3 não é ativada
        assert result.risk_score == 30

    def test_limit_time_division_60_5_and_30_1_min(self):
        """
        Testa os limites de tempo (60.5 min e 30.1 min).
        O sistema considera transações com até 60.5 min
        dentro da janela de 60 min devido ao arredondamento.
        Portanto, há 11 transações recentes e o bloqueio é ativado.
        """
        current_transaction = Transaction(500.0, self.now, "Brasil")
        previous_transactions = [
            Transaction(100.0, self.now - timedelta(minutes=30, seconds=6), "EUA")
        ]
        previous_transactions.extend(
            [Transaction(50.0, self.now - timedelta(minutes=10), "Brasil") for _ in range(10)]
        )
        previous_transactions.append(
            Transaction(50.0, self.now - timedelta(minutes=60, seconds=30), "Brasil")
        )

        blacklisted_locations = []

        result = self.system.check_for_fraud(current_transaction, previous_transactions, blacklisted_locations)

        # De acordo com a lógica atual: 11 txs → bloqueia
        assert result.is_blocked is True
        assert result.is_fraudulent is False
        assert result.risk_score == 30


    def test_limit_time_outside_61_and_30_5_min(self):
        """
        Mata:
        - M150 (R2: <= 61) -> Contaria 11 txs, bloquearia
        - M170 (R3: < 31) -> Marcaria fraude
        
        Teste: Limites fora da janela (61 min e 30.5 min).
        Original: R2 não conta (<= 60). R3 não conta (< 30).
        """
        current_transaction = Transaction(500.0, self.now, "Brasil")
        previous_transactions = [
            # R3: 30.5 min, local diferente
            Transaction(100.0, self.now - timedelta(minutes=30, seconds=30), "EUA")
        ]
        # R2: 11 txs @ 61 min
        previous_transactions.extend(
            [Transaction(50.0, self.now - timedelta(minutes=61), "Brasil") for _ in range(10)]
        )

        blacklisted_locations = []

        result = self.system.check_for_fraud(current_transaction, previous_transactions, blacklisted_locations)

        # Original: R2 (Não bloqueia, 0 txs), R3 (Não é fraude)
        assert result.is_blocked is False
        assert result.is_fraudulent is False
        assert result.risk_score == 0
