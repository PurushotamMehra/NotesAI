import 'package:flutter_test/flutter_test.dart';
import 'package:second_brain_ai/app/second_brain_app.dart';
import 'package:second_brain_ai/models/note.dart';
import 'package:second_brain_ai/screens/search_screen.dart';
import 'package:second_brain_ai/services/api_service.dart';
import 'package:second_brain_ai/widgets/memory_status_chips.dart';

import 'package:flutter/material.dart';

void main() {
  testWidgets('shows home navigation actions', (tester) async {
    await tester.pumpWidget(const SecondBrainApp());

    expect(find.text('Write one thought...'), findsOneWidget);
    expect(find.text('Add memory · now'), findsOneWidget);
    expect(find.text('View memories'), findsOneWidget);
    expect(find.text('Search memories'), findsOneWidget);
    expect(find.text('Ask your notes'), findsOneWidget);
  });

  testWidgets('shows memory status chips and retry action', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: MemoryStatusChips(
            note: _note(
              processingStatus: 'fallback',
              embeddingStatus: 'failed',
            ),
            onRetry: () {},
          ),
        ),
      ),
    );

    expect(find.text('Saved'), findsOneWidget);
    expect(find.text('AI fallback'), findsOneWidget);
    expect(find.text('Search indexing failed'), findsOneWidget);
    expect(find.text('Retry'), findsOneWidget);
  });

  testWidgets('search screen renders semantic results', (tester) async {
    await tester.pumpWidget(
      MaterialApp(home: SearchScreen(apiService: _FakeApiService())),
    );

    await tester.enterText(find.byType(TextField), 'onboarding');
    await tester.tap(find.byTooltip('Search'));
    await tester.pumpAndSettle();

    expect(find.text('Sara suggested onboarding.'), findsOneWidget);
    expect(find.textContaining('Improve first-run setup'), findsOneWidget);
    expect(find.textContaining('Person: Sara'), findsOneWidget);
    expect(find.text('Search ready'), findsOneWidget);
  });
}

class _FakeApiService extends ApiService {
  @override
  Future<List<Note>> searchNotes(String query) async {
    return [
      _note(
        summary: 'Sara suggested onboarding.',
        cleanedNote: 'Improve first-run setup for the reading app.',
        people: const ['Sara'],
        topics: const ['onboarding'],
      ),
    ];
  }
}

Note _note({
  String summary = 'Summary',
  String cleanedNote = 'Cleaned note',
  List<String> people = const [],
  List<String> topics = const [],
  String processingStatus = 'completed',
  String embeddingStatus = 'completed',
}) {
  return Note(
    id: 1,
    summary: summary,
    cleanedNote: cleanedNote,
    rawInput: cleanedNote,
    people: people,
    topics: topics,
    processingStatus: processingStatus,
    embeddingStatus: embeddingStatus,
    processingError: '',
    embeddingError: '',
  );
}
