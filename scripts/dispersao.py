# --- Script de Análise de Rede: Emergentes vs. Desenvolvidos ---
# Gera um gráfico de dispersão comparando desenvolvedores de diferentes países

# Importar as bibliotecas necessárias
import pandas as pd
import altair as alt
import os

# --- 1. Carregar o Ficheiro CSV Original ---
# Obter o diretório do script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Caminho correto: scripts/csv/network_metrics.csv
csv_path = os.path.join(script_dir, "csv", "network_metrics.csv")

try:
    df = pd.read_csv(csv_path)
    print("✓ Ficheiro 'network_metrics.csv' carregado com sucesso.")
    print(f"  Total de registos: {len(df)}")
    print(f"  Colunas disponíveis: {list(df.columns)}")
except FileNotFoundError:
    print(f"✗ Erro: Ficheiro não encontrado em '{csv_path}'.")
    print("  Certifique-se que o ficheiro está em scripts/csv/")
    exit()

# --- 2. Definir os Grupos de Países ---
emerging_countries = ["Brazil", "India"]
developed_countries = ["United States", "Germany"]
countries_of_interest = emerging_countries + developed_countries

print(f"\n📊 Países em análise:")
print(f"  Emergentes: {emerging_countries}")
print(f"  Desenvolvidos: {developed_countries}")

# --- 3. Criar a variável 'df_filtered' ---
# Filtra o DataFrame para incluir APENAS os países de interesse
df_filtered = df[df["country"].isin(countries_of_interest)].copy()
print(f"\n✓ DataFrame filtrado criado.")
print(f"  Total de desenvolvedores na análise: {len(df_filtered)}")

# Mostrar distribuição por país
if len(df_filtered) > 0:
    print("\n  Distribuição por país:")
    for country in countries_of_interest:
        count = len(df_filtered[df_filtered["country"] == country])
        print(f"    - {country}: {count} desenvolvedores")


# --- 4. Criar a nova coluna 'country_group' ---
# Mapeia cada país para seu grupo (Emergentes ou Desenvolvidos)
def map_country_group(country):
    if country in emerging_countries:
        return "Emergentes"
    elif country in developed_countries:
        return "Desenvolvidos"
    return None


df_filtered["country_group"] = df_filtered["country"].apply(map_country_group)

# Verificar se a coluna foi criada corretamente
print(f"\n✓ Coluna 'country_group' criada.")
print(f"  Grupos: {df_filtered['country_group'].unique()}")

# --- 5. Gerar o Gráfico de Dispersão ---
print("\n📈 Gerando gráfico...")

chart = (
    alt.Chart(df_filtered)
    .mark_circle(opacity=0.7)
    .encode(
        # Eixo X: Contribuição Técnica (Commits)
        x=alt.X(
            "commits_total:Q",
            title="Contribuição Técnica (Commits)",
            scale=alt.Scale(type="symlog"),
        ),
        # Eixo Y: Importância Estrutural (Betweenness)
        y=alt.Y(
            "betweenness_centrality:Q",
            title="Importância Estrutural (Betweenness)",
            scale=alt.Scale(type="symlog"),
        ),
        # Cor: Grupo de Países
        color=alt.Color(
            "country_group:N",
            title="Grupo de Países",
            scale=alt.Scale(scheme="category10"),
        ),
        # Tamanho: Indispensabilidade (Impacto da Ausência)
        size=alt.Size(
            "absence_impact:Q",
            title="Impacto da Ausência",
            scale=alt.Scale(range=[50, 1000]),
        ),
        # Tooltip: Detalhes ao passar o mouse
        tooltip=[
            alt.Tooltip("login:N", title="Utilizador"),
            alt.Tooltip("country:N", title="País"),
            alt.Tooltip("country_group:N", title="Grupo"),
            alt.Tooltip("commits_total:Q", title="Commits", format=","),
            alt.Tooltip("betweenness_centrality:Q", title="Betweenness", format=".4f"),
            alt.Tooltip("absence_impact:Q", title="Impacto Ausência", format=".4f"),
            alt.Tooltip("eigenvector_centrality:Q", title="Eigenvector", format=".4f"),
        ],
    )
    .properties(
        width=700,
        height=500,
        title={
            "text": "Análise: Centralidade vs. Contribuição (Emergentes vs. Desenvolvidos)",
            "subtitle": "Tamanho dos pontos = Impacto da Ausência | Escala logarítmica",
        },
    )
)

# --- 6. Salvar o Gráfico como PNG ---
output_path = os.path.join(script_dir, "centralidade_vs_contribuicao_grupos.png")

try:
    # Tentar salvar como PNG
    chart.save(output_path, format="png", ppi=300)
    print(f"\n✓ Gráfico PNG salvo com sucesso em: {output_path}")
except Exception as e:
    print(f"\n⚠ Erro ao salvar como PNG: {e}")
    print("  Tentando salvar como HTML interativo...")

    # Fallback: salvar como HTML
    html_path = os.path.join(script_dir, "centralidade_vs_contribuicao_grupos.html")
    chart.save(html_path)
    print(f"✓ Gráfico HTML salvo em: {html_path}")
    print("  Abra este ficheiro no navegador e tire um screenshot se necessário.")

# --- 7. Estatísticas Resumidas ---
print("\n📊 Estatísticas Resumidas:")
for group in ["Emergentes", "Desenvolvidos"]:
    group_data = df_filtered[df_filtered["country_group"] == group]
    if len(group_data) > 0:
        print(f"\n  {group}:")
        print(f"    - Média de commits: {group_data['commits_total'].mean():.2f}")
        print(
            f"    - Média de betweenness: {group_data['betweenness_centrality'].mean():.6f}"
        )
        print(
            f"    - Média de impacto ausência: {group_data['absence_impact'].mean():.6f}"
        )

print("\n✓ Análise concluída!")
