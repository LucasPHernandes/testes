// Script principal do sistema

$(document).ready(function() {
    console.log('Sistema de Refeitório iniciado!');
    
    // Inicializar tooltips do Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Inicializar popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});

// Funções utilitárias
function confirmarAcao(mensagem, callback) {
    if (confirm(mensagem)) {
        callback();
    }
}

function exportarParaCSV(dados, nomeArquivo) {
    if (!dados || dados.length === 0) {
        mostrarAlerta('warning', 'Não há dados para exportar!');
        return;
    }
    
    // Pegar cabeçalhos
    const colunas = Object.keys(dados[0]);
    
    // Criar conteúdo CSV
    let csv = colunas.join(';') + '\n';
    
    dados.forEach(item => {
        const linha = colunas.map(col => {
            const valor = item[col];
            if (typeof valor === 'string' && valor.includes(';')) {
                return `"${valor}"`;
            }
            return valor;
        }).join(';');
        csv += linha + '\n';
    });
    
    // Adicionar BOM para UTF-8
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    
    // Download
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${nomeArquivo}_${new Date().toISOString().slice(0,10)}.csv`;
    link.click();
}

function exportarParaTXT(conteudo, nomeArquivo) {
    const blob = new Blob([conteudo], { type: 'text/plain;charset=utf-8' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${nomeArquivo}_${new Date().toISOString().slice(0,10)}.txt`;
    link.click();
}

// Validações
function validarEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function validarMatricula(matricula) {
    return /^\d+$/.test(matricula);
}

function validarValor(valor) {
    return !isNaN(parseFloat(valor)) && isFinite(valor) && parseFloat(valor) > 0;
}

// Cache simples
const Cache = {
    dados: {},
    
    set(chave, valor, tempoExpiracao = 60000) {
        this.dados[chave] = {
            valor: valor,
            expiracao: Date.now() + tempoExpiracao
        };
    },
    
    get(chave) {
        const item = this.dados[chave];
        if (!item) return null;
        
        if (Date.now() > item.expiracao) {
            delete this.dados[chave];
            return null;
        }
        
        return item.valor;
    },
    
    limpar() {
        this.dados = {};
    }
};

// Gráficos
function criarGraficoPie(ctx, labels, dados, cores) {
    return new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: dados,
                backgroundColor: cores || ['#28a745', '#dc3545', '#ffc107', '#17a2b8', '#6c757d']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

function criarGraficoBar(ctx, labels, dados, label, cor) {
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: dados,
                backgroundColor: cor || '#007bff',
                borderRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        drawBorder: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

function criarGraficoLine(ctx, labels, dados, label, cor) {
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: dados,
                borderColor: cor || '#007bff',
                backgroundColor: 'rgba(0,123,255,0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}