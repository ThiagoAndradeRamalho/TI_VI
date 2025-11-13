# GRAFOS DE REDE - ANÁLISE QUESTÃO 3

## Visualizações Geradas para Análise da Centralidade em OSS

Este documento apresenta os **grafos de rede** criados para analisar se desenvolvedores de países emergentes ocupam posições de centralidade e são tecnicamente indispensáveis em projetos OSS.

---

### 📊 **GRAFOS PRINCIPAIS GERADOS**

#### 1. **network_by_country.png** - Rede de Colaboração por Tipo de País
- **Descrição**: Rede dos top 200 desenvolvedores por centralidade, coloridos por tipo de país
- **Nós**: 200 desenvolvedores (Top centralidade)
- **Cores**: 🔴 Emergentes | 🔵 Desenvolvidos | 🟡 Outros
- **Tamanho do nó**: Proporcional à centralidade de grau
- **Resultado**: Mostra sub-representação de emergentes nas posições centrais

#### 2. **centrality_networks.png** - Redes por Métricas de Centralidade
- **Duas visualizações lado a lado**:
  - **Centralidade de Grau**: Cores e tamanhos em vermelho
  - **Centralidade de Intermediação**: Cores e tamanhos em azul
- **Insight**: Revela padrões diferentes de centralidade entre os tipos

#### 3. **high_impact_network.png** - Rede de Alto Impacto
- **Foco**: 100 desenvolvedores de maior impacto (50 emergentes + 50 desenvolvidos)
- **Características**:
  - Densidade: **0.1428** (rede bem conectada)
  - **60.7%** das conexões são entre tipos diferentes (colaboração internacional)
  - **39.3%** das conexões são dentro do mesmo tipo
- **Insight**: Forte colaboração internacional entre desenvolvedores de alto impacto

#### 4. **centrality_comparison_networks.png** - Comparação Direta
- **Duas redes separadas**:
  - Top 30 países emergentes por centralidade
  - Top 30 países desenvolvidos por centralidade
- **Comparação visual**: Diferenças na estrutura e conectividade

#### 5. **country_collaboration_graph.png** - Colaboração entre Países
- **Nós**: Países com 10+ desenvolvedores
- **Tamanho**: Proporcional ao número de desenvolvedores
- **Conexões**: Baseadas em tipo de país e proximidade
- **Destaque**: Países como Índia, China, Brasil em destaque

#### 6. **degree_distribution_comparison.png** - Distribuições Estatísticas
- **Gráfico 1**: Distribuição de graus (lei de potência)
- **Gráfico 2**: Centralidade vs Contribuições técnicas
- **Análise**: Padrões diferentes entre emergentes e desenvolvidos

---

### 🔍 **PRINCIPAIS INSIGHTS DOS GRAFOS**

#### **1. Estrutura da Rede**
- **Densidade geral**: 0.0722 (rede esparsa típica de redes sociais)
- **Distribuição**: 77% desenvolvidos, 15.5% emergentes na amostra central
- **Conectividade**: Boa colaboração internacional

#### **2. Posições Centrais**
- **Emergentes estão presentes** em todas as métricas de centralidade
- **Sub-representação clara** nas posições de maior destaque
- **Padrões de cluster** diferentes entre tipos de país

#### **3. Colaboração Internacional**
- **60.7%** das conexões de alto impacto são internacionais
- **Forte integração** entre desenvolvedores emergentes e desenvolvidos
- **Redes complementares** mais do que competitivas

#### **4. Distribuição de Impacto**
- **Lei de potência** na distribuição de graus para ambos os grupos
- **Emergentes concentrados** em posições intermediárias
- **Desenvolvidos dominam** as posições de maior centralidade

---

### 📈 **ESTATÍSTICAS DAS REDES GERADAS**

| Rede | Nós | Arestas | Densidade | Emergentes % |
|------|-----|---------|-----------|--------------|
| **Principal** | 200 | 1,436 | 0.0722 | 15.5% |
| **Alto Impacto** | 100 | 707 | 0.1428 | 50.0%* |
| **Por País** | 25 | 45 | 0.15 | 40.0% |

*Balanceado intencionalmente para análise comparativa

---

### 🎯 **EVIDÊNCIAS VISUAIS PARA A QUESTÃO 3**

#### ✅ **SIM, ocupam posições de centralidade**
- Presença visual consistente em todos os grafos
- Participação ativa nas redes de colaboração
- Conexões internacionais significativas

#### ⚠️ **Mas com limitações**
- **Sub-representação visual** nas posições mais centrais
- **Clusters menos densos** comparados aos países desenvolvidos
- **Centralidade média menor** (visível nos tamanhos dos nós)

#### 🤝 **Colaboração forte**
- **60.7% de conexões internacionais** entre grupos de alto impacto
- **Redes complementares** mais do que isoladas
- **Integração crescente** no ecossistema OSS

---

### 💡 **COMO INTERPRETAR OS GRAFOS**

1. **Tamanho dos nós** = Centralidade/Impacto
2. **Cores** = Tipo de país (Vermelho = Emergente, Azul = Desenvolvido)
3. **Espessura das arestas** = Força da colaboração
4. **Posição na rede** = Importância estrutural
5. **Densidade de clusters** = Concentração de influência

---

### 📁 **ARQUIVOS DISPONÍVEIS**

Todos os grafos estão salvos em `/results/question3/` com alta resolução (300 DPI) para análise detalhada e apresentação.

**Conclusão dos Grafos**: As visualizações confirmam que desenvolvedores de países emergentes **SIM, ocupam posições de centralidade** na rede OSS, mas revelam uma **sub-representação sistemática** nas posições de maior influência, oferecendo evidência visual clara para as conclusões quantitativas da análise.