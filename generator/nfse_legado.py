"""Adaptador para NFS-e no padrao municipal legado, pre-ADN-nacional (Ginfes v03).

Complementa `generator/danfse.py` (padrao nacional novo, NT 008/2026): gera o
envelope de envio de lote de RPS (Recibo Provisorio de Servicos) no formato
Ginfes, um dos ~60 padroes municipais suportados pela lib `nfselib-legacy`
(import `nfselib`) usados por prefeituras que ainda nao migraram para o ADN
nacional.
"""

import random
from decimal import Decimal

from faker import Faker
from nfselib.ginfes.bindings.servico_enviar_lote_rps_envio_v03 import (
    EnviarLoteRpsEnvio,
)
from nfselib.ginfes.bindings.tipos_v03 import (
    TcCpfCnpj,
    TcDadosServico,
    TcDadosTomador,
    TcEndereco,
    TcIdentificacaoPrestador,
    TcIdentificacaoRps,
    TcIdentificacaoTomador,
    TcInfRps,
    TcLoteRps,
    TcRps,
    TcValores,
)
from xsdata.formats.dataclass.serializers import XmlSerializer
from xsdata.formats.dataclass.serializers.config import SerializerConfig

from generator import fake_data

_SERIALIZER_CONFIG = SerializerConfig(pretty_print=False, xml_declaration=False)
_SERIALIZER = XmlSerializer(config=_SERIALIZER_CONFIG)

_SERVICE_CATALOG = [
    ("01.05", "Suporte tecnico em informatica e manutencao de bancos de dados"),
    ("14.01", "Manutencao e reparo predial"),
    ("17.05", "Assessoria e consultoria contabil"),
    ("01.02", "Desenvolvimento de software sob encomenda"),
    ("07.01", "Limpeza e conservacao"),
]


def generate_nfse_legado(seed=None, cnpj_alnum_ratio=fake_data.DEFAULT_CNPJ_ALNUM_RATIO):
    rng = random.Random(seed)
    faker = Faker("pt_BR")
    faker.seed_instance(seed)

    cnpj_prestador = fake_data.cnpj(rng, alnum_ratio=cnpj_alnum_ratio)
    inscricao_municipal = str(rng.randint(1, 99999999))
    numero_rps = str(rng.randint(1, 999999))

    pessoa_fisica = rng.random() < 0.3
    if pessoa_fisica:
        cpf_cnpj_tomador = fake_data.cpf(rng)
        cpf_cnpj = TcCpfCnpj(Cpf=cpf_cnpj_tomador)
        razao_social_tomador = fake_data.person_name(rng, faker)
    else:
        cpf_cnpj_tomador = fake_data.cnpj(rng, alnum_ratio=cnpj_alnum_ratio)
        cpf_cnpj = TcCpfCnpj(Cnpj=cpf_cnpj_tomador)
        razao_social_tomador = fake_data.company_name(rng, faker)

    endereco_tomador = fake_data.address(rng, faker)
    emissao = fake_data.recent_datetime(rng)

    item_lista_servico, discriminacao = rng.choice(_SERVICE_CATALOG)
    v_serv = round(rng.uniform(200, 30000), 2)
    aliquota = rng.choice([Decimal("2.00"), Decimal("3.00"), Decimal("5.00")])
    v_iss = round(v_serv * float(aliquota) / 100, 2)

    endereco_kwargs = {
        "Endereco": endereco_tomador["street"],
        "Numero": endereco_tomador["number"],
        "Bairro": endereco_tomador["neighborhood"],
        "CodigoMunicipio": int(endereco_tomador["municipality_code"]),
        "Uf": endereco_tomador["uf"],
        "Cep": int(endereco_tomador["cep"]),
    }
    if endereco_tomador["complement"]:
        endereco_kwargs["Complemento"] = endereco_tomador["complement"]

    rps = TcRps(
        InfRps=TcInfRps(
            IdentificacaoRps=TcIdentificacaoRps(
                Numero=int(numero_rps), Serie="1", Tipo="1"
            ),
            DataEmissao=emissao.strftime("%Y-%m-%dT%H:%M:%S"),
            NaturezaOperacao="1",
            OptanteSimplesNacional=rng.choice(["1", "2"]),
            IncentivadorCultural="2",
            Status="1",
            Servico=TcDadosServico(
                Valores=TcValores(
                    ValorServicos=Decimal(f"{v_serv:.2f}"),
                    IssRetido="2",
                    ValorIss=Decimal(f"{v_iss:.2f}"),
                    Aliquota=aliquota,
                ),
                ItemListaServico=item_lista_servico,
                Discriminacao=discriminacao,
                CodigoMunicipio=int(endereco_tomador["municipality_code"]),
            ),
            Prestador=TcIdentificacaoPrestador(
                Cnpj=cnpj_prestador, InscricaoMunicipal=inscricao_municipal
            ),
            Tomador=TcDadosTomador(
                IdentificacaoTomador=TcIdentificacaoTomador(CpfCnpj=cpf_cnpj),
                RazaoSocial=razao_social_tomador,
                Endereco=TcEndereco(**endereco_kwargs),
            ),
            Id=f"rps:{numero_rps}",
        )
    )

    envio = EnviarLoteRpsEnvio(
        LoteRps=TcLoteRps(
            NumeroLote=rng.randint(1, 999999),
            Cnpj=cnpj_prestador,
            InscricaoMunicipal=inscricao_municipal,
            QuantidadeRps=1,
            ListaRps=TcLoteRps.ListaRps(Rps=[rps]),
            Id=f"lote:{numero_rps}",
        )
    )

    xml_str = _SERIALIZER.render(envio)

    field_values = {
        "cnpj_prestador": cnpj_prestador,
        "inscricao_municipal": inscricao_municipal,
        "numero_rps": numero_rps,
        "cpf_cnpj_tomador": cpf_cnpj_tomador,
        "razao_social_tomador": razao_social_tomador,
        "municipality_name": endereco_tomador["municipality_name"],
        "dEmissao": emissao.isoformat(),
        "item_lista_servico": item_lista_servico,
        "discriminacao": discriminacao,
        "v_serv": v_serv,
        "v_iss": v_iss,
    }
    return xml_str, field_values
