import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:aix_os/main.dart';

void main() {
  testWidgets('App starts', (WidgetTester tester) async {
    await tester.pumpWidget(const AixOsApp());
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
