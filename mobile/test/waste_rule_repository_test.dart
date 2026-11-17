import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ecosort/features/knowledge_base/waste_rule_model.dart';
import 'package:ecosort/features/knowledge_base/waste_rule_repository.dart';

void main() {
  late WasteRuleRepository repo;
  late List<String> labels;

  setUpAll(() {
    final rulesFile = File('assets/kb/rules.json');
    expect(rulesFile.existsSync(), isTrue,
        reason: 'mobile/assets/kb/rules.json must exist');
    repo = WasteRuleRepository.fromJsonString(rulesFile.readAsStringSync());

    final labelsFile = File('assets/kb/labels.txt');
    expect(labelsFile.existsSync(), isTrue,
        reason: 'mobile/assets/kb/labels.txt must exist');
    labels = labelsFile
        .readAsLinesSync()
        .map((l) => l.trim())
        .where((l) => l.isNotEmpty)
        .toList();
  });

  group('WasteRuleRepository — 20-Class Contract & CV 9368 Rules', () {
    test('loads all 20 canonical classes in 1:1 parity with labels.txt', () {
      expect(repo.totalClasses, 20);
      expect(repo.rules.length, 20);
      expect(labels.length, 20);

      for (var i = 0; i < 20; i++) {
        final item = repo.lookupByIndex(i);
        expect(item, isNotNull);
        expect(item!.classIndex, i);
        expect(item.itemId, labels[i]);
        expect(repo.lookupById(item.itemId), same(item));
      }
      expect(repo.lookupByIndex(99), isNull);
      expect(repo.lookupById('non_existent'), isNull);
    });

    test('resolves all 80 (class x isClean x hasFood) truth-table combinations', () {
      for (final rule in repo.rules) {
        for (final isClean in [true, false]) {
          for (final hasFood in [true, false]) {
            final decision = repo.resolveState(
              rule,
              isClean: isClean,
              hasFood: hasFood,
            );
            expect(decision.instructionsVi.isNotEmpty, isTrue);
            expect(decision.ttsReadoutVi.isNotEmpty, isTrue);
            expect(decision.legalCitation.isNotEmpty, isTrue);
          }
        }
      }
    });

    test('enforces CV 9368/BTNMT-KSONMT mappings (3.3.1, 3.1.1, 1.4.3 vs 3.3.5)', () {
      // Mục 3.3.1: Bã trà/cà phê & Vỏ trứng -> Rác sinh hoạt khác
      final tea = repo.lookupById('ba_tra_ca_phe')!;
      expect(repo.resolveState(tea, isClean: false, hasFood: false).stream,
          WasteStream.residualWaste);

      final egg = repo.lookupById('vo_trung')!;
      expect(repo.resolveState(egg, isClean: false, hasFood: false).stream,
          WasteStream.residualWaste);

      // Mục 3.1.1 vs 3.3.3: Khẩu trang người bệnh -> hazardous alert
      final mask = repo.lookupById('khau_trang_y_te')!;
      final normalMask = repo.resolveState(mask, isClean: true, hasFood: false);
      final sickMask = repo.resolveState(mask, isClean: false, hasFood: false);
      expect(normalMask.isHazardous, isFalse);
      expect(sickMask.isHazardous, isTrue);
      expect(sickMask.displayColor, const Color(0xFFB42318));

      // Mục 1.4.3 vs 3.3.5: Thủy tinh vỡ -> Tái chế; Sành sứ vỡ -> Rác khác
      final shards = repo.lookupById('manh_gom_su_thuy_tinh_vo')!;
      final brokenGlass =
          repo.resolveState(shards, isClean: true, hasFood: false);
      final brokenCeramic =
          repo.resolveState(shards, isClean: false, hasFood: false);
      expect(brokenGlass.stream, WasteStream.recyclable);
      expect(brokenGlass.displayColor, const Color(0xFFC2410C));
      expect(brokenCeramic.stream, WasteStream.residualWaste);
      expect(brokenCeramic.displayColor, const Color(0xFF4B5563));
    });

    test('bridges PhysicalState enum from ClarificationDialog cleanly', () {
      final milkCarton = repo.lookupById('hop_sua_giay')!;
      expect(
        repo.resolvePhysicalState(milkCarton, PhysicalState.clean).stream,
        WasteStream.recyclable,
      );
      expect(
        repo.resolvePhysicalState(milkCarton, PhysicalState.dirty).stream,
        WasteStream.residualWaste,
      );
      expect(
        repo
            .resolvePhysicalState(milkCarton, PhysicalState.liquidRemaining)
            .stream,
        WasteStream.residualWaste,
      );
    });

    test('supports Vietnamese diacritic and unsigned alias search', () {
      // Exact accented alias ("vỏ chuối" -> rau_cu_qua_thua)
      final accented = repo.search('vỏ chuối');
      expect(accented.any((r) => r.itemId == 'rau_cu_qua_thua'), isTrue);

      // Unsigned ASCII alias ("vo chuoi" -> rau_cu_qua_thua)
      final unsigned = repo.search('vo chuoi');
      expect(unsigned.any((r) => r.itemId == 'rau_cu_qua_thua'), isTrue);

      // Accented "bã cà phê" & unsigned "hop sua"
      expect(repo.search('bã cà phê').first.itemId, 'ba_tra_ca_phe');
      expect(repo.search('hop sua').first.itemId, 'hop_sua_giay');
      expect(repo.search('sành sứ').first.itemId, 'manh_gom_su_thuy_tinh_vo');
    });

    test('asset bundle loader works inside widget test environment', () async {
      TestWidgetsFlutterBinding.ensureInitialized();
      final loaded = await WasteRuleRepository.loadFromAsset();
      expect(loaded.rules.length, 20);
    });
  });
}
