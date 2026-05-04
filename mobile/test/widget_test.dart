import 'package:flutter_test/flutter_test.dart';
import 'package:second_brain_ai/app/second_brain_app.dart';

void main() {
  testWidgets('shows core navigation placeholders', (tester) async {
    await tester.pumpWidget(const SecondBrainApp());

    expect(find.text('Capture a note'), findsOneWidget);
    expect(find.text('Capture'), findsOneWidget);
    expect(find.text('Notes'), findsOneWidget);
    expect(find.text('Chat'), findsOneWidget);

    await tester.tap(find.text('Notes'));
    await tester.pump();

    expect(find.text('No notes yet'), findsOneWidget);
  });
}
