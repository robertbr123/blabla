from ondeline_api.services.pii_mask import mask_pii


def test_cpf_masked() -> None:
    assert "[CPF]" in mask_pii("meu cpf eh 111.222.333-44")
    assert "[CPF]" in mask_pii("11122233344")


def test_cnpj_masked() -> None:
    assert "[CNPJ]" in mask_pii("12.345.678/0001-90")


def test_phone_masked() -> None:
    assert "[PHONE]" in mask_pii("liga 11 99999-9999")
    assert "[PHONE]" in mask_pii("+55 11 988887777")


def test_email_masked() -> None:
    assert "[EMAIL]" in mask_pii("manda pra a@b.com")


def test_no_match_passthrough() -> None:
    assert mask_pii("ola mundo") == "ola mundo"


def test_empty() -> None:
    assert mask_pii("") == ""
