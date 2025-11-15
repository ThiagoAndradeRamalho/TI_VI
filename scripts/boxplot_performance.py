# --- Script para Geração do Boxplot de Performance (FILTRADO) ---
#
# Objetivo: Gerar um gráfico de caixa (boxplot) INTERATIVO usando Altair
# que compara 'performance_score' entre 'developed' e 'emerging',
# MAS APENAS para os países específicos do estudo.
#
# Países do Estudo:
# - Emergentes: 'Brazil', 'India'
# - Desenvolvidos: 'United States', 'Germany'

import pandas as pd
import altair as alt
import os

print("=" * 80)
print("Visualização: Boxplot de Performance (FILTRADO)")
print("Comparação: Brasil/Índia vs. EUA/Alemanha")
print("=" * 80)

# --- 1. Carregar os Dados ---
# Obter o diretório do script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Caminho correto para o CSV
csv_path = os.path.join(script_dir, "csv", "performance_scores.csv")

try:
    df_perf = pd.read_csv(csv_path)
    print(f"\n✓ Ficheiro 'performance_scores.csv' carregado com sucesso.")
    print(f"  Total de registos originais: {len(df_perf)}")
except FileNotFoundError:
    print(f"\n✗ Erro: Ficheiro não encontrado em '{csv_path}'.")
    print("  Certifique-se que o ficheiro está em scripts/csv/")
    exit()

# --- 2. NOVO: Definir e Filtrar os Países do Estudo ---
# Esta é a etapa crucial que pediste
countries_of_interest = ["Brazil", "India", "United States", "Germany"]

# Filtra o DataFrame. O 'df_filtered' conterá APENAS dados desses 4 países.
df_filtered = df_perf[df_perf["country"].isin(countries_of_interest)].copy()

print(f"\n📍 Filtro aplicado para os países: {countries_of_interest}")
print(f"  Total de desenvolvedores na análise FILTRADA: {len(df_filtered)}")

# Verificar distribuição por país
print(f"\n📊 Distribuição por país (filtrado):")
for country in countries_of_interest:
    count = len(df_filtered[df_filtered["country"] == country])
    print(f"  - {country}: {count} desenvolvedores")

# --- Traduzir os rótulos para português (apenas para visualização) ---
df_filtered["country_type_pt"] = df_filtered["country_type"].map(
    {"developed": "Desenvolvido", "emerging": "Emergente"}
)

print(f"\n📈 Estatísticas de Performance Score (dados filtrados):")
print(f"  - Média geral: {df_filtered['performance_score'].mean():.6f}")
print(f"  - Mediana geral: {df_filtered['performance_score'].median():.6f}")
print(f"  - Mínimo: {df_filtered['performance_score'].min():.6f}")
print(f"  - Máximo: {df_filtered['performance_score'].max():.6f}")

# --- 3. Gerar o Gráfico de Caixa (Boxplot) com a Escala Correta ---
print("\n🎨 Gerando o gráfico boxplot FILTRADO com escala 'symlog'...")

chart = (
    alt.Chart(df_filtered)
    .mark_boxplot()
    .encode(
        # Eixo X (Categórico) - USANDO A COLUNA TRADUZIDA
        x=alt.X(
            "country_type_pt:N",
            title="Grupo de Países",
            axis=alt.Axis(labelAngle=0),
        ),
        # Eixo Y (Numérico)
        # Usando 'symlog' para a visualização correta.
        y=alt.Y(
            "performance_score:Q",
            title="Performance Score (Escala Log)",
            scale=alt.Scale(type="symlog", constant=0.01),
        ),
        # Cor baseada no grupo - USANDO A COLUNA TRADUZIDA
        color=alt.Color(
            "country_type_pt:N",
            title="Grupo de Países",
            scale=alt.Scale(
                domain=["Desenvolvido", "Emergente"],
                range=[
                    "#3498DB",
                    "#E74C3C",
                ],  # Azul para desenvolvido, Vermelho para emergente
            ),
        ),
        # Tooltip para detalhes interativos - USANDO A COLUNA TRADUZIDA
        tooltip=[
            alt.Tooltip("login:N", title="Desenvolvedor"),
            alt.Tooltip("country:N", title="País"),
            alt.Tooltip("country_type_pt:N", title="Grupo"),
            alt.Tooltip("performance_score:Q", title="Score", format=".5f"),
        ],
    )
    .properties(
        width=600,
        height=450,
        title={
            "text": "Comparação de Performance",
        },
    )
    .interactive()
)  # Torna o gráfico interativo

# --- 4. Salvar o Gráfico ---
output_json = os.path.join(script_dir, "performance_boxplot_FILTRADO.json")
output_html = os.path.join(script_dir, "performance_boxplot_FILTRADO.html")

try:
    # Salvar como JSON
    chart.save(output_json)
    print(f"\n✓ Gráfico JSON salvo em: {output_json}")
    print("  Este JSON gera o boxplot focado apenas nos 4 países do estudo.")

    # Salvar também como HTML
    chart.save(output_html)
    print(f"✓ Gráfico HTML salvo em: {output_html}")
    print("  Abra este ficheiro no navegador para visualização interativa.")

except Exception as e:
    print(f"\n✗ Erro ao salvar gráfico: {e}")

# --- 5. Estatísticas Detalhadas por Grupo (Filtrado) ---
print("\n" + "=" * 80)
print("ESTATÍSTICAS DETALHADAS POR GRUPO (DADOS FILTRADOS)")
print("=" * 80)

for group in ["developed", "emerging"]:
    group_data = df_filtered[df_filtered["country_type"] == group]["performance_score"]
    group_label = "DESENVOLVIDO" if group == "developed" else "EMERGENTE"

    # Identificar quais países estão nesse grupo
    countries_in_group = df_filtered[df_filtered["country_type"] == group][
        "country"
    ].unique()

    print(f"\n{group_label} ({', '.join(countries_in_group)}):")
    print(f"  - Contagem: {len(group_data)}")
    print(f"  - Média: {group_data.mean():.6f}")
    print(f"  - Mediana: {group_data.median():.6f}")
    print(f"  - Desvio Padrão: {group_data.std():.6f}")
    print(f"  - Mínimo: {group_data.min():.6f}")
    print(f"  - Máximo: {group_data.max():.6f}")
    print(f"  - Q1 (25%): {group_data.quantile(0.25):.6f}")
    print(f"  - Q3 (75%): {group_data.quantile(0.75):.6f}")

print("\n" + "=" * 80)
print("✓ Análise concluída!")
print("Gráfico focado nos 4 países: Brazil, India, United States, Germany")
print("=" * 80)
