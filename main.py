from pyscript import document, when

iron = 0


def update_ui():
    iron_text = document.querySelector("#iron")
    iron_text.innerText = str(iron)


@when("click", "#mine-button")
def mine_iron(event):
    global iron

    iron += 1
    update_ui()


update_ui()