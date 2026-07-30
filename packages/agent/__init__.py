"""The ReAct kernel, shared by the chatbot and the console.

This lives below apps/ rather than inside apps/chatbot because both apps have to
run the exact same loop: the chatbot serves it to users, the console runs it
against the golden dataset. If the console imported the chatbot the control
plane and the serving plane would depend on each other, and "the benchmark ran
the same code production runs" would stop being structurally true.
"""
