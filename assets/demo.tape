# Graba assets/demo.gif: vhs assets/demo.tape (desde la raíz del repo)
Output assets/demo.gif
Set Shell "bash"
Set FontSize 16
Set Width 1000
Set Height 560
Set Padding 16
Set Theme "Dracula"
Set TypingSpeed 45ms

Hide
Type `export HOME=$(mktemp -d) LANG=es_AR.UTF-8 PS1='$ ' R=$PWD && D=$(mktemp -d) && cd $D && git init -q . && reinstack() { python3 $R/reinstack.py "$@"; } && clear`
Enter
Show

Type "reinstack install . --agent claude"
Enter
Sleep 3s
Type "clear"
Enter
Type "ls -A"
Enter
Sleep 2s
Type "head -n 12 CONTEXTO.md"
Enter
Sleep 4s
Type "clear"
Enter
Type "head -n 14 ORQUESTADOR.md"
Enter
Sleep 5s
