import 'package:flutter/material.dart';

import '../features/chat/chat_screen.dart';
import '../features/notes/note_input_screen.dart';
import '../features/notes/notes_list_screen.dart';

class SecondBrainApp extends StatelessWidget {
  const SecondBrainApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Second Brain AI',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF256D5A),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      home: const AppShell(),
    );
  }
}

class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _selectedIndex = 0;

  static const _screens = [NoteInputScreen(), NotesListScreen(), ChatScreen()];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Second Brain AI')),
      body: SafeArea(child: _screens[_selectedIndex]),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) {
          setState(() {
            _selectedIndex = index;
          });
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.add_circle_outline),
            selectedIcon: Icon(Icons.add_circle),
            label: 'Capture',
          ),
          NavigationDestination(
            icon: Icon(Icons.library_books_outlined),
            selectedIcon: Icon(Icons.library_books),
            label: 'Notes',
          ),
          NavigationDestination(
            icon: Icon(Icons.chat_bubble_outline),
            selectedIcon: Icon(Icons.chat_bubble),
            label: 'Chat',
          ),
        ],
      ),
    );
  }
}
