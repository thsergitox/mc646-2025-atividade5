# Análise dos Novos Casos de Teste e do Mutante Equivalente

Este documento detalha os novos casos de teste implementados para o sistema `FlightBookingSystem` e explica a razão pela qual o mutante 110 é considerado equivalente.

## Arquivo de Teste
**Localização:** `tests/test_flight_booking_system.py`

## Implementações para FlightBookingSystem

Para o sistema de reservas de voos, foram implementados os seguintes casos de teste para cobrir os **casos de limite (boundary cases)** que os testes originais não contemplavam. Os mutantes sobreviveram precisamente porque essas condições de limite não estavam sendo testadas.

### test_booking_with_exact_available_seats
**Linha:** 178  
**Mutante eliminado:** `78`  
**Lógica original:** `if passengers > available_seats:` (linha 28)  
**Mutação:** `if passengers >= available_seats:`

Os testes anteriores verificavam casos onde havia mais passageiros que assentos (reserva falha) e menos passageiros que assentos (reserva bem-sucedida). No entanto, não havia um teste para o cenário exato onde `passengers == available_seats`. Neste caso, a reserva deve ser bem-sucedida. O mutante (`>=`) faria com que a reserva falhasse neste caso de limite. Este teste garante que, quando o número de passageiros é exatamente igual ao de assentos disponíveis (no teste, 5 e 5), o `result.confirmation` seja `True`, eliminando assim o mutante que o teria tornado `False`.

### test_group_discount_boundary_no_discount_for_4_passengers
**Linha:** 191  
**Mutante eliminado:** `97`  
**Lógica original:** `if passengers > 4:` (linha 43)  
**Mutação:** `if passengers >= 4:`

Este teste foca-se no limite inferior para o desconto de grupo. O código original não dá desconto a um grupo de 4 pessoas. O mutante, por outro lado, daria o desconto. Este teste cria uma reserva para exatamente 4 passageiros e verifica se o preço final não tem o desconto de 5%. Isso demonstra que a lógica original está correta e a do mutante está incorreta.

### test_group_discount_boundary_with_discount_for_5_passengers
**Linha:** 204  
**Mutante eliminado:** `98`  
**Lógica original:** `if passengers > 4:` (linha 43)  
**Mutação:** `if passengers > 5:`

Este é o complemento do teste anterior, verificando o limite superior. O código original sim, dá um desconto a um grupo de 5. O mutante, por outro lado, não o daria (esperaria até ter 6). Este teste cria uma reserva para exatamente 5 passageiros e verifica se o preço final sim, inclui o desconto de 5%, eliminando o mutante que teria calculado o preço sem desconto.

### test_reward_points_boundary_with_one_point
**Linha:** 217  
**Mutante eliminado:** `103`  
**Lógica original:** `if reward_points_available > 0:` (linha 47)  
**Mutação:** `if reward_points_available > 1:`

A lógica para usar pontos de recompensa é ativada se tiver mais de 0 pontos. O mutante altera esta condição para exigir mais de 1 ponto. Os testes não incluíam um caso onde fosse usado exatamente 1 ponto. Este teste faz isso. Verifica que com `reward_points_available=1`, `points_used` é `True` e o preço é reduzido em `0.01`. O mutante não teria aplicado o desconto.

### test_cancellation_at_full_refund_boundary
**Linha:** 230  
**Mutantes eliminados:** `114` e `115`  
**Lógica original:** `if hours_to_departure >= 48:` (linha 57)  
**Mutações:** `if hours_to_departure > 48:` e `if hours_to_departure >= 49:`

Para obter um reembolso total, o cancelamento deve ser feito com 48 horas ou mais de antecedência. Os mutantes alteram este requisito. Os testes não verificavam o que acontecia se o cancelamento fosse feito exatamente com 48 horas de antecedência. Este teste faz isso e afirma que o `refund_amount` deve ser o preço total (reembolso completo). Os mutantes teriam calculado um reembolso parcial, pelo que o `assert` falharia e os eliminaria.

## Por que o Mutante 110 é Equivalente?

*   **Linha de código:** `53` em `src/flight/FlightBookingSystem.py`
*   **Lógica original:** `if final_price < 0:`
*   **Mutação:** `if final_price <= 0:`
*   **Código que se executa se for `True`:** `final_price = 0`

Um mutante é "equivalente" quando, apesar de o código ser diferente, o resultado observável do programa é sempre o mesmo. Não existe nenhuma entrada que possa produzir uma saída diferente entre o original e o mutante.

A razão pela qual este mutante é 'equivalente' é que, independentemente do valor de `final_price`, o resultado final do código é sempre o mesmo. Se analisarmos os cenários possíveis, vemos que tanto para preços positivos (como 10) quanto para preços negativos (como -10), as duas condições (`< 0` e `<= 0`) levam ao mesmo resultado: o preço ou se mantém positivo, ou é corrigido para zero em ambos os casos.

O ponto crucial está no caso de limite, quando `final_price` é exatamente `0`. Na versão original do código, a condição `0 < 0` é falsa, e o valor permanece `0`. Na versão mutada, a condição `0 <= 0` é verdadeira, o que leva o código a definir o preço como `0` — um valor que ele já possuía.

Como o estado final da variável é idêntico em todas as situações imagináveis, torna-se impossível criar um teste que passe numa versão e falhe na outra, e é por isso que o mutante 'sobrevive' de forma inevitável.
