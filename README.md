# Farm Animal 3D Web Generator

Interface web para gerar modelos STL de animais de fazenda (Bovino, Equino, Suíno, Ave, Ovino) prontos para impressão 3D.

## Funcionalidades

- **5 espécies**: Bovino, Equino, Suíno, Ave, Ovino
- **Dois modos**:
  - **Sólido**: modelo único (um arquivo STL)
  - **Articulado**: peças separadas com juntas móveis (bola-soquete / pino)
- **Escala ajustável**: padrão 10 mm → modelo ~10×5×7 cm (cabe na mão)
- **Download em ZIP**: arquivos STL organizados + guia de montagem (para articulados)
- **Sem dependências externas** no gerador (apenas Python padrão + Flask para web)

## Como rodar localmente

```bash
# 1. Clone o repositório
git clone https://github.com/dataloggertiete-hub/farm-animal-3d-web.git
cd farm-animal-3d-web/farm_animal_web

# 2. Crie e ative um ambiente virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Execute a aplicação
python app.py
```

Acesse **http://127.0.0.1:5000** no navegador.

## Deploy

### Render (gratuito)
1. Conecte este repositório no [Render](https://render.com)
2. New → Web Service
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `python app.py`

### Docker
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY farm_animal_web/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY farm_animal_web/ .
EXPOSE 5000
CMD ["python", "app.py"]
```

```bash
docker build -t farm-animal-3d .
docker run -p 5000:5000 farm-animal-3d
```

## Estrutura do projeto

```
farm_animal_web/
├── app.py              # Servidor Flask
├── gerador.py          # Lógica de geração 3D (STL)
├── requirements.txt    # Flask
├── templates/
│   └── index.html      # Formulário web
├── static/             # (opcional) CSS/JS extras
└── generated/          # Arquivos temporários (ignorados no git)
```

## Como funciona

1. Usuário escolhe a espécie, escala e tipo (sólido/articulado)
2. O Flask chama `gerador.py` que cria a geometria paramétrica
3. STL(s) são salvos em pasta temporária única (UUID)
4. Tudo é zipado e entregue como download
5. Pasta temporária pode ser limpa periodicamente

## Exemplos de uso

| Espécie | Escala (mm) | Tamanho aprox. |
|---------|-------------|----------------|
| Bovino  | 10          | 10 × 5 × 7 cm  |
| Equino  | 10          | 10 × 5 × 7 cm  |
| Suíno   | 10          | 10 × 5 × 7 cm  |
| Ave     | 10          | 8 × 4 × 5 cm   |
| Ovino   | 10          | 9 × 4 × 6 cm   |

## Licença

MIT - Use livremente para projetos pessoais, educacionais ou comerciais.

## Autor

Desenvolvido para dataloggertiete-hub