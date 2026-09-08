import hello

def test_hello(capsys):
    hello.main()
    captured = capsys.readouterr()
    assert captured.out.strip() == "Hello PythonGPT"
