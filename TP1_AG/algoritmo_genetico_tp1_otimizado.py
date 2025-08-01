# -*- coding: utf-8 -*-
"""Algoritmo_Genetico-Otimizado2.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1q3fr0ylLBCNvNXvWZ_LU0iYGGjGhS8QO
"""

# -*- coding: utf-8 -*-
"""Algoritmo Genético -TP1 (Otimizado)"""

import random
import matplotlib.pyplot as plt
from google.colab import drive
import numpy as np # Importar numpy para cálculo da média e regressão e GA
import time
import heapq # Importado para seleção eficiente

# Monta o Google Drive para acesso aos arquivos
try:
    drive.mount('/content/drive')
except:
    print("Google Drive já montada ou erro ao montar.")


# Representa um item com peso e valor
class Item:
    def __init__(self, nome, peso, valor):
        self.nome = nome
        self.peso = peso
        self.valor = valor

# Representa um indivíduo (solução candidata)
class Individuo:
    # Adicionado item_pesos_np, item_valores_np para performance
    def __init__(self, itens, capacidade, item_pesos_np, item_valores_np, genes=None):
        self.itens = itens # Mantém para referência (nomes, etc.)
        self.capacidade = capacidade
        self.item_pesos_np = item_pesos_np # NumPy array de pesos dos itens
        self.item_valores_np = item_valores_np # NumPy array de valores dos itens
        self.num_itens = len(itens)

        if genes is not None: # genes deve ser um NumPy array
            self.genes = genes.copy() # Garante que seja uma cópia
        else:
            self.genes = self._gerar_genes_validos() # Retorna NumPy array
        self.avaliar_fitness()

    def _gerar_genes_validos(self):
        genes = np.zeros(self.num_itens, dtype=np.int8)
        indices = np.arange(self.num_itens)
        np.random.shuffle(indices) # Embaralha os índices in-place
        peso_total_atual = 0
        for i in indices:
            if peso_total_atual + self.item_pesos_np[i] <= self.capacidade:
                genes[i] = 1
                peso_total_atual += self.item_pesos_np[i]
        return genes

    def avaliar_fitness(self):
        # Cálculo vetorizado com NumPy para maior performance
        self.peso_total = np.dot(self.item_pesos_np, self.genes)
        self.valor_total = np.dot(self.item_valores_np, self.genes)
        self.fitness = self.valor_total if self.peso_total <= self.capacidade else 0

    def crossover(self, outro):
        # Ponto de corte aleatório
        ponto = random.randint(1, self.num_itens - 1)
        # Criação dos filhos usando concatenação de NumPy arrays
        filho1_genes = np.concatenate((self.genes[:ponto], outro.genes[ponto:]))
        filho2_genes = np.concatenate((outro.genes[:ponto], self.genes[ponto:]))
        # Cria novos indivíduos passando os arrays NumPy de pesos e valores
        return (Individuo(self.itens, self.capacidade, self.item_pesos_np, self.item_valores_np, filho1_genes),
                Individuo(self.itens, self.capacidade, self.item_pesos_np, self.item_valores_np, filho2_genes))

    def mutar(self, taxa_mutacao):
        # Cria uma máscara booleana para os genes que sofrerão mutação
        mutation_mask = np.random.random(self.num_itens) < taxa_mutacao
        # Aplica a mutação: inverte o valor do gene (0->1, 1->0)
        self.genes[mutation_mask] = 1 - self.genes[mutation_mask]
        self.avaliar_fitness() # Reavalia o fitness após a mutação

    def corrigir(self):
        # Se já for válido, não há nada a fazer
        if self.peso_total <= self.capacidade:
            return

        # Encontra os índices dos itens atualmente na mochila (gene == 1)
        indices_ativos = np.where(self.genes == 1)[0]

        if indices_ativos.size == 0: # Nenhum item na mochila, mas ainda acima do peso (improvável com itens de peso > 0)
            if self.peso_total > self.capacidade: # Confirmação
                self.fitness = 0 # Fitness deve ser zero
            return

        np.random.shuffle(indices_ativos) # Embaralha para remover itens aleatoriamente

        # Remove itens um por um até que o peso esteja dentro da capacidade
        for idx_para_remover in indices_ativos:
            if self.peso_total <= self.capacidade: # Verifica se já é válido
                break

            # Remove o item e atualiza peso e valor incrementalmente
            if self.genes[idx_para_remover] == 1: # Confere se o item ainda está marcado para remoção
                self.genes[idx_para_remover] = 0
                self.peso_total -= self.item_pesos_np[idx_para_remover]
                self.valor_total -= self.item_valores_np[idx_para_remover]

        # Recalcula o fitness final com base no peso e valor atualizados
        # Se após as remoções o peso ainda exceder a capacidade, o fitness será 0.
        self.fitness = self.valor_total if self.peso_total <= self.capacidade else 0


# População de indivíduos
class Populacao:
    def __init__(self, tamanho, itens, capacidade, item_pesos_np, item_valores_np):
        self.itens = itens
        self.capacidade = capacidade
        self.tamanho = tamanho
        self.item_pesos_np = item_pesos_np # Armazena os arrays NumPy
        self.item_valores_np = item_valores_np
        # Cria indivíduos passando os arrays NumPy
        self.individuos = [Individuo(itens, capacidade, item_pesos_np, item_valores_np) for _ in range(tamanho)]

    def selecao(self):
        # Filtra indivíduos válidos (dentro da capacidade)
        candidatos_validos = [ind for ind in self.individuos if ind.peso_total <= self.capacidade]

        if len(candidatos_validos) >= 2:
            # Usa heapq.nlargest para obter os 2 melhores de forma eficiente
            return heapq.nlargest(2, candidatos_validos, key=lambda ind: ind.fitness)
        elif self.individuos: # Se não houver pelo menos 2 válidos, pega os 2 melhores da população inteira
             # Garante que retornará indivíduos mesmo que a população seja menor que 2
            num_to_select = min(2, len(self.individuos))
            return heapq.nlargest(num_to_select, self.individuos, key=lambda ind: ind.fitness)
        return [] # Caso a população esteja vazia


    def nova_geracao(self, taxa_crossover=0.8, num_elites=2):
        nova_pop = []
        # Garante que o número de elites não exceda o tamanho da população
        num_elites = min(num_elites, len(self.individuos), self.tamanho)

        if self.individuos and num_elites > 0:
            # Adiciona os indivíduos de elite à nova população usando heapq.nlargest

            # Em Populacao.nova_geracao(), para o elitismo:
            elite = heapq.nlargest(num_elites, self.individuos, key=lambda ind: (ind.fitness, ind.peso_total if ind.fitness > 0 else -1))

            #elite = heapq.nlargest(num_elites, self.individuos, key=lambda ind: ind.fitness)
            nova_pop.extend(elite)

        # Gera o restante da população através de seleção, crossover e mutação
        while len(nova_pop) < self.tamanho:
            pais = self.selecao()
            if not pais or len(pais) < 2 : # Se não conseguir selecionar pais suficientes
                # Preenche com indivíduos aleatórios ou cópias da elite se disponível
                if nova_pop: # usa um da elite como fallback para criar mais
                     # Cria um novo indivíduo baseado no primeiro da elite (ou o melhor disponível) com pequena variação
                    fallback_genes = nova_pop[0].genes.copy()
                    # Perturba um pouco para evitar duplicatas diretas se for o único modo de gerar
                    mask = np.random.random(len(fallback_genes)) < 0.1 # pequena chance de mutação
                    fallback_genes[mask] = 1 - fallback_genes[mask]
                    filho_fallback = Individuo(self.itens, self.capacidade, self.item_pesos_np, self.item_valores_np, fallback_genes)
                    filho_fallback.corrigir()
                    nova_pop.append(filho_fallback)
                    if len(nova_pop) >= self.tamanho: break
                    # Tenta gerar o segundo da mesma forma ou quebra se não der
                    if len(nova_pop) < self.tamanho:
                        fallback_genes2 = nova_pop[0].genes.copy()
                        mask2 = np.random.random(len(fallback_genes2)) < 0.15
                        fallback_genes2[mask2] = 1 - fallback_genes2[mask2]
                        filho_fallback2 = Individuo(self.itens, self.capacidade, self.item_pesos_np, self.item_valores_np, fallback_genes2)
                        filho_fallback2.corrigir()
                        nova_pop.append(filho_fallback2)

                elif self.individuos : # Se não há elite, mas há indivíduos na população antiga
                     # Pega os melhores disponíveis da população atual como pais
                     pais_fallback = heapq.nlargest(min(2, len(self.individuos)), self.individuos, key=lambda ind: ind.fitness)
                     if len(pais_fallback) == 1: # se só tem um, duplica para "cruzar"
                         pais = [pais_fallback[0], pais_fallback[0]]
                     else:
                         pais = pais_fallback # agora tem dois pais
                else: # População inicial vazia e sem elite, não deveria acontecer se tam_pop > 0
                    break # Sai do loop se não puder gerar mais indivíduos

            # Se pais foram selecionados (ou fallback), prossegue com crossover/mutação
            if len(pais) == 2 :
                if random.random() < taxa_crossover:
                    filhos = pais[0].crossover(pais[1])
                else: # Se não houver crossover, os filhos são cópias (mutadas) dos pais
                    # Garante que os genes são copiados para os novos indivíduos
                    filhos = (Individuo(self.itens, self.capacidade, self.item_pesos_np, self.item_valores_np, pais[0].genes.copy()),
                              Individuo(self.itens, self.capacidade, self.item_pesos_np, self.item_valores_np, pais[1].genes.copy()))

                for filho in filhos:
                    filho.mutar(taxa_mutacao=0.2) # A taxa de mutação estava hardcoded, poderia ser parâmetro
                    filho.corrigir()
                    nova_pop.append(filho)
                    if len(nova_pop) >= self.tamanho:
                        break
            elif len(nova_pop) == 0 and not self.individuos : # Se não há como popular, quebra
                break


        # Se a nova_pop for maior que o tamanho desejado, seleciona os melhores.
        # Usa heapq.nlargest para manter os 'self.tamanho' melhores indivíduos.
        if len(nova_pop) > self.tamanho:
            self.individuos = heapq.nlargest(self.tamanho, nova_pop, key=lambda ind: ind.fitness)
        elif nova_pop: # Se nova_pop não estiver vazia mas menor ou igual ao tamanho
            self.individuos = nova_pop
        # Se nova_pop estiver vazia (e.g., população inicial zero), individuos permanece como estava (vazio).

    def melhor_individuo(self):
        if not self.individuos:
            return None # Ou um indivíduo padrão com fitness 0
        return max(self.individuos, key=lambda ind: ind.fitness)

# Carrega dados do arquivo
def carregar_dados(caminho):
    with open(caminho, 'r') as f:
        capacidade = int(f.readline())
        num_itens = int(f.readline()) # Não usado diretamente aqui, mas bom para saber
        itens = []
        for linha in f:
            nome, peso, valor = linha.strip().split(',')
            itens.append(Item(nome, int(peso), int(valor)))
    return capacidade, itens

# Algoritmo genético
def algoritmo_genetico(caminho_arquivo, tam_populacao=100, max_geracoes=50, taxa_crossover=0.8, taxa_mutacao_ind=0.01, num_elites=2):
    random.seed() # Semente para reprodutibilidade se um valor fixo for passado, senão aleatório
    np.random.seed() # Semente para NumPy também

    capacidade, itens_obj = carregar_dados(caminho_arquivo)

    if not itens_obj:
        print("Nenhum item carregado. Verifique o arquivo de dados.")
        return None, []

    # Cria arrays NumPy para pesos e valores uma vez
    item_pesos_np = np.array([item.peso for item in itens_obj])
    item_valores_np = np.array([item.valor for item in itens_obj])

    populacao = Populacao(tam_populacao, itens_obj, capacidade, item_pesos_np, item_valores_np)

    historico = []

    for geracao in range(max_geracoes):
        populacao.nova_geracao(taxa_crossover, num_elites) # taxa_mutacao_ind é usada dentro de nova_geracao->filho.mutar
        melhor_da_geracao = populacao.melhor_individuo()

        if melhor_da_geracao: # Verifica se um melhor indivíduo foi encontrado
            historico.append([geracao + 1, melhor_da_geracao.fitness, melhor_da_geracao.peso_total])
            print(f"Geração {geracao + 1}: Melhor valor = {melhor_da_geracao.fitness}, Peso = {melhor_da_geracao.peso_total}")
        else: # População pode ter se tornado vazia ou não produzir indivíduos válidos
            print(f"Geração {geracao + 1}: Nenhum indivíduo válido encontrado.")
            historico.append([geracao + 1, 0, 0]) # Registra fitness 0
            # break # Pode ser útil parar se a população colapsar


    melhor_final = populacao.melhor_individuo()
    return melhor_final, historico

def main():
  numero_execucoes = 30
  taxa_crossover_ag = 0.8
  taxa_mutacao_individuo = 0.01 # Definindo a taxa de mutação por indivíduo
  num_elites_ag = 2

  todos_historicos = []
  melhores_individuos_por_execucao = [] # Para estatísticas finais

  print(f"Executando o Algoritmo Genético {numero_execucoes} vezes com taxa de crossover {taxa_crossover_ag}, mutação {taxa_mutacao_individuo} e {num_elites_ag} elites...")

  start_time_total = time.perf_counter()

  for i in range(numero_execucoes):
    print(f"\n--- Execução {i+1} ---")
    start_time_exec = time.perf_counter()
    # Passa a taxa de mutação para o algoritmo_genetico
    melhor, historico_execucao = algoritmo_genetico(
        '/content/drive/MyDrive/Colab Notebooks/TP1_AG_Problema_Mochila/dados/KNAPDATA100000.TXT', # Ajuste o caminho se necessário
        tam_populacao=100,       # Pode aumentar para testes com 10000 indivíduos
        max_geracoes=50,       # Aumente para permitir convergência
        taxa_crossover=taxa_crossover_ag,
        taxa_mutacao_ind=taxa_mutacao_individuo,
        num_elites=num_elites_ag
    )
    end_time_exec = time.perf_counter()
    print(f"Tempo da execução {i+1}: {end_time_exec - start_time_exec:.2f} segundos.")

    if melhor:
        todos_historicos.append(historico_execucao)
        melhores_individuos_por_execucao.append(melhor) # Salva o melhor indivíduo da execução

        print("Melhor solução encontrada na execução:")
        print(f"Valor total: {melhor.fitness}")
        print(f"Peso total: {melhor.peso_total} de {melhor.capacidade}")
        # print("Itens selecionados:") # Descomente para ver os itens
        # for item_obj, gene in zip(melhor.itens, melhor.genes):
        #           if gene:
        #             print(f"- {item_obj.nome} (peso={item_obj.peso}, valor={item_obj.valor})")
    else:
        print("Nenhuma solução encontrada na execução.")
        # Adiciona um histórico vazio ou com zeros para não quebrar as análises
        # Assumindo que max_geracoes foi o número de gerações tentadas
        max_ger = 100 # O valor de max_geracoes usado em algoritmo_genetico
        todos_historicos.append([[g+1, 0, 0] for g in range(max_ger)])


  end_time_total = time.perf_counter()
  total_time = end_time_total - start_time_total
  print(f"\n--- Tempo de Execução Total das {numero_execucoes} execuções ---")
  print(f"O algoritmo levou {total_time:.2f} segundos para completar.")

  # --- Análises e Gráficos ---
  # (O código de plotagem e estatísticas permanece o mesmo,
  #  apenas garanta que ele lida com `todos_historicos` corretamente,
  #  especialmente se algumas execuções não produzirem históricos completos)

  if not todos_historicos:
      print("Nenhum histórico de execução disponível para gerar gráficos.")
      return

  # Calcular a média de fitness por geração
  # Verifica se há históricos para processar
  # Garante que todos os históricos tenham o mesmo número de gerações para cálculo simples da média
  # Se não, precisa de uma lógica mais robusta ou padronizar o tamanho do histórico (ex: preencher com último valor)
  min_geracoes_em_historicos = min(len(h) for h in todos_historicos) if todos_historicos else 0

  if min_geracoes_em_historicos > 0:
      medias_por_geracao = np.zeros(min_geracoes_em_historicos)
      melhores_por_geracao = np.full(min_geracoes_em_historicos, -np.inf)
      piores_por_geracao = np.full(min_geracoes_em_historicos, np.inf)

      fitness_por_geracao_para_desvio = [[] for _ in range(min_geracoes_em_historicos)]

      for historico_execucao in todos_historicos:
          for geracao in range(min_geracoes_em_historicos):
              fitness_atual = historico_execucao[geracao][1]
              medias_por_geracao[geracao] += fitness_atual
              melhores_por_geracao[geracao] = max(melhores_por_geracao[geracao], fitness_atual)
              piores_por_geracao[geracao] = min(piores_por_geracao[geracao], fitness_atual)
              fitness_por_geracao_para_desvio[geracao].append(fitness_atual)

      medias_por_geracao /= numero_execucoes
      desvios_por_geracao = [np.std(fitness_list) for fitness_list in fitness_por_geracao_para_desvio]

      geracoes_plot = np.arange(1, min_geracoes_em_historicos + 1)

      # Gráfico 1: Média de Fitness com Curva de Tendência
      plt.figure(figsize=(10, 6))
      plt.plot(geracoes_plot, medias_por_geracao, 'o-', label='Média por Geração')
      if min_geracoes_em_historicos > 3 : # Polyfit precisa de pontos suficientes
          coeficientes_media = np.polyfit(geracoes_plot, medias_por_geracao, min(3, min_geracoes_em_historicos -1))
          polinomio_media = np.poly1d(coeficientes_media)
          plt.plot(geracoes_plot, polinomio_media(geracoes_plot), '-', label='Curva de Tendência (Média)', color='red')
      plt.xlabel("Geração")
      plt.ylabel("Média de Fitness")
      plt.title("Evolução da Média de Fitness por Geração")
      plt.grid(True)
      plt.legend()
      plt.show()

      # Gráfico 2: Melhor, Pior Fitness e Curva de Tendência da Média
      plt.figure(figsize=(10, 6))
      plt.plot(geracoes_plot, medias_por_geracao, 'o-', label='Média por Geração', color='blue')
      if min_geracoes_em_historicos > 3 :
          plt.plot(geracoes_plot, polinomio_media(geracoes_plot), '-', label='Curva de Tendência (Média)', color='red') # Reusa o polinomio_media
      plt.plot(geracoes_plot, melhores_por_geracao, '-', label='Melhor por Geração', color='green')
      plt.plot(geracoes_plot, piores_por_geracao, '-', label='Pior por Geração', color='orange')
      plt.xlabel("Geração")
      plt.ylabel("Fitness")
      plt.title("Evolução do Fitness (Melhor, Pior, Média) por Geração")
      plt.grid(True)
      plt.legend()
      plt.show()

      # Gráfico 3: Desvio Padrão por Geração
      plt.figure(figsize=(10, 6))
      plt.plot(geracoes_plot, desvios_por_geracao, '-', label='Desvio Padrão por Geração', color='purple')
      plt.xlabel("Geração")
      plt.ylabel("Desvio Padrão do Fitness")
      plt.title("Evolução do Desvio Padrão do Fitness por Geração")
      plt.grid(True)
      plt.legend()
      plt.show()
  else:
      print("Não há dados suficientes nos históricos para gerar os gráficos de evolução.")


  # Estatísticas finais sobre os melhores indivíduos de cada execução
  if melhores_individuos_por_execucao:
      todos_fitness_finais = np.array([ind.fitness for ind in melhores_individuos_por_execucao])
      melhor_fitness_geral = np.max(todos_fitness_finais)
      pior_fitness_geral = np.min(todos_fitness_finais)
      media_fitness_geral = np.mean(todos_fitness_finais)
      desvio_fitness_geral = np.std(todos_fitness_finais)

      # Encontrar o melhor indivíduo geral
      # melhor_individuo_geral = max(melhores_individuos_por_execucao, key=lambda ind: ind.fitness)

      print(f"\n--- Estatísticas Finais das {numero_execucoes} Execuções (baseado no melhor de cada execução) ---")
      print(f"Melhor fitness geral encontrado: {melhor_fitness_geral}")
      # print("Itens na melhor mochila geral:") # Descomente para detalhes
      # for item_obj, gene in zip(melhor_individuo_geral.itens, melhor_individuo_geral.genes):
      #     if gene:
      #         print(f"  - {item_obj.nome} (peso: {item_obj.peso}, valor: {item_obj.valor})")
      print(f"Pior fitness (dos melhores de cada execução): {pior_fitness_geral}")
      print(f"Média de fitness (dos melhores de cada execução): {media_fitness_geral:.2f}")
      print(f"Desvio padrão do fitness (dos melhores de cada execução): {desvio_fitness_geral:.2f}")

      # Gráfico 4: Boxplot dos Fitness Finais
      plt.figure(figsize=(8, 6))
      plt.boxplot(todos_fitness_finais, vert=True, patch_artist=True, tick_labels=["Fitness Final por Execução"])
      plt.title("Distribuição do Melhor Fitness de Cada Execução")
      plt.ylabel("Fitness")
      plt.grid(True)

      # Identificar outliers para exibição no print (opcional)
      q1 = np.percentile(todos_fitness_finais, 25)
      q3 = np.percentile(todos_fitness_finais, 75)
      iqr = q3 - q1
      limite_inferior = q1 - 1.5 * iqr
      limite_superior = q3 + 1.5 * iqr
      outliers = todos_fitness_finais[(todos_fitness_finais < limite_inferior) | (todos_fitness_finais > limite_superior)]
      if outliers.size > 0:
          print("Outliers detectados nos fitness finais:", outliers.tolist())
      plt.show()
  else:
      print("Nenhum indivíduo foi retornado pelas execuções para estatísticas finais e boxplot.")


if __name__ == "__main__":
    main()